import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel
import jwt

from auth import (
    register_user,
    login_user,
    get_google_auth_url,
    exchange_code_for_token,
    get_google_user_info,
    store_oauth_state,
    consume_oauth_state,
)
import secrets
from auth_db import upsert_google_user, get_user_by_email

router = APIRouter()

def get_jwt_secret():
    secret = os.getenv("JWT_SECRET")
    if not secret:
        # Fallback only for tests
        if "PYTEST_CURRENT_TEST" in os.environ:
            return "unisearch-super-secret-key"
        raise RuntimeError("CRITICAL: JWT_SECRET environment variable is not set!")
    return secret

JWT_ALGORITHM = "HS256"
COOKIE_NAME = "access_token"

# --- Schemas ---
class RegisterRequest(BaseModel):
    email: str
    display_name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleCallbackRequest(BaseModel):
    code: str
    state: str

# --- Helpers ---
def create_jwt_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt

def set_auth_cookie(response: Response, token: str):
    is_secure = os.getenv("SECURE_COOKIE", "False").lower() in ("true", "1", "yes")
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/",
        samesite="lax",
        secure=is_secure,
    )

def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = get_user_by_email(email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_optional(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if not user_id or not email:
            return None
        return get_user_by_email(email)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

# --- Endpoints ---

@router.post("/register")
def register(req: RegisterRequest, response: Response):
    user, error = register_user(req.email, req.display_name, req.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Create token
    token = create_jwt_token({"sub": user["id"], "email": user["email"]})
    set_auth_cookie(response, token)
    return {"status": "success", "user": user}

@router.post("/login")
def login(req: LoginRequest, response: Response):
    user, error = login_user(req.email, req.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    token = create_jwt_token({"sub": user["id"], "email": user["email"]})
    set_auth_cookie(response, token)
    return {"status": "success", "user": user}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, samesite="lax")
    return {"status": "success"}

@router.get("/google/url")
def get_google_url():
    state = secrets.token_urlsafe(32)
    store_oauth_state(state)
    url = get_google_auth_url(state)
    return {"url": url}

@router.post("/google/callback")
def google_callback(req: GoogleCallbackRequest, response: Response):
    try:
        if not consume_oauth_state(req.state):
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
            
        access_token = exchange_code_for_token(req.code)
        google_user = get_google_user_info(access_token)
        
        if not google_user.get("email_verified", False):
            raise HTTPException(status_code=400, detail="Google email is not verified")
            
        email = google_user.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google account has no email")
            
        user = upsert_google_user(
            email=email,
            display_name=google_user.get("name", ""),
            avatar_url=google_user.get("picture", "")
        )
        
        token = create_jwt_token({"sub": user["id"], "email": user["email"]})
        set_auth_cookie(response, token)
        
        safe_user = {k: v for k, v in user.items() if k != "password_hash"}
        return {"status": "success", "user": safe_user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google Auth Failed: {str(e)}")

@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    # Remove sensitive fields
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return {"status": "success", "user": safe_user}
