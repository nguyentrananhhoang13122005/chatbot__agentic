import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, before_sleep_log
import logging

logger = logging.getLogger(__name__)

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

def _ensure_api_key():
    global OPENROUTER_API_KEY
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "missing-openrouter-api-key":
        load_dotenv(override=True)
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        if OPENROUTER_API_KEY:
            client.api_key = OPENROUTER_API_KEY
    return OPENROUTER_API_KEY


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


# ======== TENACITY: Auto-retry cho 429 Too Many Requests ========
def _is_retryable_error(error):
    """Kiểm tra xem lỗi có nên retry không (429, connection, timeout)."""
    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return True
    if isinstance(error, APIStatusError):
        status_code = _status_code_from_error(error)
        return status_code in (429, 500, 502, 503, 504)
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_openrouter_api(request_kwargs: dict):
    """Gọi OpenRouter API với tenacity auto-retry (tối đa 3 lần, nghỉ 2 giây giữa mỗi lần)."""
    return client.chat.completions.create(**request_kwargs)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_openrouter_api_stream(request_kwargs: dict):
    """Gọi OpenRouter API stream với tenacity auto-retry (tối đa 3 lần, nghỉ 2 giây giữa mỗi lần)."""
    return client.chat.completions.create(**request_kwargs)


def validate_api_key() -> tuple[bool, str]:
    key = _ensure_api_key()
    if not key or not key.strip():
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
    key = _ensure_api_key()
    if not key or not key.strip():
        return None, _build_error_info("missing_api_key")

    models = model_list or OPENROUTER_FALLBACK_MODELS
    last_error = None

    for model_name in models:
        try:
            request_kwargs = {
                "messages": messages,
                "model": model_name,
                "temperature": temperature,
            }
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens

            # tenacity tự động retry tối đa 3 lần (nghỉ 2s) nếu gặp 429/connection/timeout
            completion = _call_openrouter_api(request_kwargs)
            content = completion.choices[0].message.content
            return (content.strip() if content else ""), None

        except AuthenticationError as error:
            error_info = _build_error_info("unauthorized", str(error), model_name, _status_code_from_error(error))
            print(f"ERROR [LLM {model_name}]: {error_info['message']}")
            return None, error_info

        except RateLimitError as error:
            # Tenacity đã retry 3 lần mà vẫn 429 → chuyển sang model tiếp theo
            error_info = _build_error_info("rate_limit", str(error), model_name, 429)
            last_error = error_info
            print(f"⚠️ [LLM {model_name}]: Rate limit sau 3 lần retry → thử model tiếp theo")
            continue

        except APIStatusError as error:
            error_info = _classify_status_error(error, model_name)
            last_error = error_info
            if error_info["type"] in {"unauthorized", "quota_exceeded"}:
                print(f"ERROR [LLM {model_name}]: {error_info['message']}")
                return None, error_info
            print(f"⚠️ [LLM {model_name}]: {error_info['message']} → thử model tiếp theo")
            continue

        except (APIConnectionError, APITimeoutError) as error:
            # Tenacity đã retry 3 lần mà vẫn lỗi kết nối → chuyển model
            error_info = _build_error_info("connection_error", str(error), model_name)
            last_error = error_info
            print(f"⚠️ [LLM {model_name}]: Connection error sau 3 lần retry → thử model tiếp theo")
            continue

        except Exception as error:
            error_info = _build_error_info("unknown", str(error), model_name)
            last_error = error_info
            print(f"ERROR [LLM {model_name}]: {error_info['message']} {error_info['detail']}")
            continue

    return None, last_error or _build_error_info("unknown")


def call_llm_stream(
    messages: list,
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int | None = None,
):
    key = _ensure_api_key()
    if not key or not key.strip():
        yield FRIENDLY_ERROR_MESSAGES["missing_api_key"]
        return

    model_name = model or OPENROUTER_FALLBACK_MODELS[0]
    yielded_any = False

    try:
        request_kwargs = {
            "messages": messages,
            "model": model_name,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens

        # tenacity tự động retry tối đa 3 lần (nghỉ 2s) nếu gặp 429/connection/timeout
        stream = _call_openrouter_api_stream(request_kwargs)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yielded_any = True
                yield chunk.choices[0].delta.content

        if not yielded_any:
            content, error_info = call_llm(
                messages=messages,
                model_list=OPENROUTER_FALLBACK_MODELS,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if content:
                yield content
            elif error_info:
                yield error_info["message"]

    except Exception as error:
        print(f"ERROR [LLM Stream {model_name}]: {error}")
        if yielded_any:
            yield "\n\n⚠️ Kết nối AI bị gián đoạn trong lúc truyền dữ liệu. Vui lòng thử lại nếu câu trả lời chưa đầy đủ."
            return

        # Tenacity đã retry 3 lần stream mà vẫn lỗi → fallback sang non-stream call_llm (có retry riêng)
        print(f"⚠️ [LLM Stream {model_name}]: Stream failed sau retry → fallback sang non-stream")
        content, error_info = call_llm(
            messages=messages,
            model_list=OPENROUTER_FALLBACK_MODELS,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if content:
            yield content
        elif error_info:
            yield error_info["message"]
