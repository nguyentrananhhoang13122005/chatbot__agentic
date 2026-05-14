import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_FALLBACK_MODELS = [
    "qwen/qwen3-8b",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-3-1b-it:free",
]

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY or "missing-openrouter-api-key",
    timeout=10,
)

FRIENDLY_ERROR_MESSAGES = {
    "missing_api_key": "⚠️ Chưa cấu hình OpenRouter API key. Vui lòng thêm OPENROUTER_API_KEY vào file môi trường trước khi dùng tính năng AI.",
    "unauthorized": "⚠️ OpenRouter API key không hợp lệ hoặc đã hết quyền truy cập. Vui lòng kiểm tra lại cấu hình API key.",
    "quota_exceeded": "⚠️ Hệ thống đã vượt giới hạn sử dụng AI hoặc tài khoản OpenRouter đã hết quota. Vui lòng thử lại sau hoặc cập nhật quota.",
    "rate_limit": "⚠️ Hệ thống AI đang nhận quá nhiều yêu cầu. Vui lòng thử lại sau vài giây.",
    "server_error": "⚠️ Dịch vụ AI đang gặp sự cố tạm thời. Hệ thống sẽ dùng dữ liệu có sẵn nếu có thể.",
    "connection_error": "⚠️ Không thể kết nối tới dịch vụ AI. Vui lòng kiểm tra mạng và thử lại.",
    "unknown": "⚠️ Hệ thống AI tạm thời không khả dụng. Vui lòng thử lại sau.",
}


def _build_error_info(error_type: str, detail: str = "", model: str = "", status_code=None) -> dict:
    return {
        "type": error_type,
        "message": FRIENDLY_ERROR_MESSAGES.get(error_type, FRIENDLY_ERROR_MESSAGES["unknown"]),
        "detail": detail,
        "model": model,
        "status_code": status_code,
    }


def _status_code_from_error(error) -> int:
    status_code = getattr(error, "status_code", None)
    if status_code is None and getattr(error, "response", None) is not None:
        status_code = getattr(error.response, "status_code", None)
    try:
        return int(status_code) if status_code is not None else 0
    except (TypeError, ValueError):
        return 0


def _classify_status_error(error, model: str) -> dict:
    status_code = _status_code_from_error(error)
    detail = str(error)
    if status_code in (401, 403):
        return _build_error_info("unauthorized", detail, model, status_code)
    if status_code == 402:
        return _build_error_info("quota_exceeded", detail, model, status_code)
    if status_code == 429:
        return _build_error_info("rate_limit", detail, model, status_code)
    if status_code >= 500:
        return _build_error_info("server_error", detail, model, status_code)
    return _build_error_info("unknown", detail, model, status_code)


def _should_retry(error_info: dict) -> bool:
    return error_info.get("type") in {"rate_limit", "server_error", "connection_error"}


def _retry_delay(error_info: dict, attempt_index: int) -> int:
    if error_info.get("type") == "server_error":
        return [1, 3][min(attempt_index, 1)]
    return [2, 4][min(attempt_index, 1)]


def validate_api_key() -> tuple[bool, str]:
    if not OPENROUTER_API_KEY or not OPENROUTER_API_KEY.strip():
        return False, FRIENDLY_ERROR_MESSAGES["missing_api_key"]

    _, error_info = call_llm(
        messages=[{"role": "user", "content": "ping"}],
        model_list=[OPENROUTER_FALLBACK_MODELS[0]],
        temperature=0.0,
        max_tokens=1,
        max_retries=0,
    )
    if error_info:
        return False, error_info["message"]
    return True, ""


def call_llm(
    messages: list,
    model_list: list | None = None,
    temperature: float = 0.1,
    max_tokens: int | None = None,
    max_retries: int = 2,
) -> tuple[str | None, dict | None]:
    if not OPENROUTER_API_KEY or not OPENROUTER_API_KEY.strip():
        return None, _build_error_info("missing_api_key")

    models = model_list or OPENROUTER_FALLBACK_MODELS
    last_error = None

    for model_name in models:
        attempt = 0
        while attempt <= max_retries:
            try:
                request_kwargs = {
                    "messages": messages,
                    "model": model_name,
                    "temperature": temperature,
                }
                if max_tokens is not None:
                    request_kwargs["max_tokens"] = max_tokens

                completion = client.chat.completions.create(**request_kwargs)
                content = completion.choices[0].message.content
                return (content.strip() if content else ""), None

            except AuthenticationError as error:
                error_info = _build_error_info("unauthorized", str(error), model_name, _status_code_from_error(error))
                print(f"ERROR [LLM {model_name}]: {error_info['message']} {error_info['detail']}")
                return None, error_info

            except RateLimitError as error:
                error_info = _build_error_info("rate_limit", str(error), model_name, _status_code_from_error(error) or 429)
                last_error = error_info

            except APIStatusError as error:
                error_info = _classify_status_error(error, model_name)
                last_error = error_info
                if error_info["type"] in {"unauthorized", "quota_exceeded"}:
                    print(f"ERROR [LLM {model_name}]: {error_info['message']} {error_info['detail']}")
                    return None, error_info

            except (APIConnectionError, APITimeoutError) as error:
                error_info = _build_error_info("connection_error", str(error), model_name)
                last_error = error_info

            except Exception as error:
                error_info = _build_error_info("unknown", str(error), model_name)
                last_error = error_info
                print(f"ERROR [LLM {model_name}]: {error_info['message']} {error_info['detail']}")
                break

            if _should_retry(last_error) and attempt < max_retries:
                delay = _retry_delay(last_error, attempt)
                print(f"⏳ Retry {attempt + 1}/{max_retries} for {model_name} after {delay}s: {last_error['message']}")
                time.sleep(delay)
                attempt += 1
                continue

            print(f"ERROR [LLM {model_name}]: {last_error['message']} {last_error.get('detail', '')}")
            break

    return None, last_error or _build_error_info("unknown")
