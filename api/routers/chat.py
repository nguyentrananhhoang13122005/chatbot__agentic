from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import uuid

from api.routers.auth import get_current_user_optional
from chat_db import (
    save_session,
    list_sessions,
    load_session_for_user,
    delete_session,
    rename_session,
    toggle_bookmark,
)

router = APIRouter()


class SessionCreateRequest(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    messages: List[dict] = Field(default_factory=list)


class SessionUpdateRequest(BaseModel):
    title: str


@router.get("/sessions")
def get_sessions(user: Optional[dict] = Depends(get_current_user_optional)):
    """Lấy danh sách các phiên chat gần nhất của người dùng hiện tại."""
    if not user:
        return []
    return list_sessions(limit=50, user_id=user["id"])


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    """Lấy danh sách tin nhắn của một phiên chat cụ thể."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để xem lịch sử.")
    messages = load_session_for_user(session_id, user_id=user["id"])
    return {
        "id": session_id,
        "messages": messages,
    }


@router.post("/sessions")
def create_or_update_session(req: SessionCreateRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    """Lưu hoặc cập nhật một phiên chat."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để lưu lịch sử.")
    session_id = req.id or str(uuid.uuid4())
    save_session(
        session_id=session_id,
        messages=req.messages,
        title=req.title,
        user_id=user["id"],
    )
    return {
        "status": "success",
        "id": session_id,
    }


@router.put("/sessions/{session_id}/title")
def rename_chat_session(session_id: str, req: SessionUpdateRequest, user: Optional[dict] = Depends(get_current_user_optional)):
    """Đổi tên tiêu đề của một phiên chat."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    ok = rename_session(session_id, req.title, user_id=user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")
    return {"status": "success"}


@router.delete("/sessions/{session_id}")
def remove_chat_session(session_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    """Xóa một phiên chat."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    ok = delete_session(session_id, user_id=user["id"])
    return {"status": "success", "deleted": ok}


@router.post("/sessions/{session_id}/bookmark")
def bookmark_chat_session(session_id: str, user: Optional[dict] = Depends(get_current_user_optional)):
    """Ghim hoặc bỏ ghim một phiên chat."""
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    new_state = toggle_bookmark(session_id, user_id=user["id"])
    return {"status": "success", "bookmarked": new_state}
