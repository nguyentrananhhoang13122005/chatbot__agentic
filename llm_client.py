import os
import threading
import time
import random
from dotenv import load_dotenv
from openai import OpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError
from tenacity import Retrying, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type, before_sleep_log
import logging

logger = logging.getLogger(__name__)

load_dotenv(override=True)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return float(default)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Danh sách model đọc từ env LLM_MODELS (phân tách bằng dấu phẩy) để đổi model mà không cần sửa code.
# Model cũ bị OpenRouter gỡ (404) sẽ không còn làm sập hệ thống: client tự chuyển sang model kế tiếp.
_DEFAULT_MODELS = [
    "qwen/qwen3.7-flash",
    "qwen/qwen3.7-plus",
    "google/gemma-4-31b-it:free",
]
OPENROUTER_FALLBACK_MODELS = [
    m.strip() for m in os.getenv("LLM_MODELS", "").split(",") if m.strip()
] or _DEFAULT_MODELS

# Timeout theo từng lần gọi. Mặc định cũ 10s quá ngắn cho prompt dài / model suy luận.
LLM_TIMEOUT = _env_float("LLM_TIMEOUT", 45)
# Số lần thử LẠI tối đa cho lỗi tạm thời (429/kết nối/timeout) trên MỖI model.
LLM_MAX_RETRIES = int(_env_float("LLM_MAX_RETRIES", 1))
# Qwen 3.x mặc định bật "thinking" → TTFT hàng chục giây. Bài toán tra cứu không cần.
LLM_DISABLE_REASONING = _env_bool("LLM_DISABLE_REASONING", True)

# max_retries=0: tắt retry ngầm của SDK. Retry chỉ do tenacity kiểm soát ở một chỗ duy nhất,
# tránh nhân lồng (SDK x tenacity) khiến một lần lỗi kéo dài hàng chục giây.
client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY or "missing-openrouter-api-key",
    timeout=LLM_TIMEOUT,
    max_retries=0,
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
    "model_unavailable": "⚠️ Model AI đang được cấu hình không còn khả dụng (đã bị nhà cung cấp gỡ hoặc đổi tên). Quản trị viên cần cập nhật biến LLM_MODELS.",
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
    if status_code == 404 or (status_code == 400 and "model" in detail.lower()):
        # Model bị gỡ/đổi tên: phải thấy rõ nguyên nhân thật thay vì "unknown".
        return _build_error_info("model_unavailable", detail, model, status_code)
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


# ======== TENACITY: Auto-retry cho 429 / lỗi kết nối / timeout ========
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


def _retrying(max_retries: int) -> Retrying:
    """Tạo bộ retry: (max_retries + 1) lần thử, backoff mũ + jitter để nhiều request không đập cùng lúc."""
    return Retrying(
        stop=stop_after_attempt(max(0, max_retries) + 1),
        wait=wait_exponential_jitter(initial=1, max=6),
        # RateLimitError KHÔNG retry cùng model: 429 từ pool dùng chung thường kéo dài; chuyển sang model kế tiếp nhanh hơn.
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def _apply_model_options(request_kwargs: dict, model_name: str) -> dict:
    """Gắn tuỳ chọn riêng cho từng model (hiện tại: tắt chế độ suy luận để giảm độ trễ)."""
    if LLM_DISABLE_REASONING and "free" not in model_name:
        extra = dict(request_kwargs.get("extra_body") or {})
        extra.setdefault("reasoning", {"enabled": False})
        request_kwargs["extra_body"] = extra
    return request_kwargs


def _call_openrouter_api(request_kwargs: dict, max_retries: int = LLM_MAX_RETRIES):
    """Gọi OpenRouter API; retry có kiểm soát cho lỗi tạm thời."""
    return _retrying(max_retries)(client.chat.completions.create, **request_kwargs)


def _call_openrouter_api_stream(request_kwargs: dict, max_retries: int = LLM_MAX_RETRIES):
    """Gọi OpenRouter API stream; retry có kiểm soát cho lỗi tạm thời (chỉ khi chưa nhận byte nào)."""
    return _retrying(max_retries)(client.chat.completions.create, **request_kwargs)


# ---- Circuit breaker nhẹ: model vừa lỗi sẽ bị đặt xuống cuối danh sách trong LLM_COOLDOWN_SECONDS ----
# Vẫn được thử nếu tất cả model đều đang cooldown (không bao giờ tự khóa toàn hệ thống).
LLM_COOLDOWN_SECONDS = _env_float("LLM_COOLDOWN_SECONDS", 60)
_cooldown_until: dict[str, float] = {}
_cooldown_lock = threading.Lock()


def _order_models(models: list) -> list:
    now = time.time()
    with _cooldown_lock:
        healthy = [m for m in models if _cooldown_until.get(m, 0) <= now]
        cooling = [m for m in models if _cooldown_until.get(m, 0) > now]
    return healthy + cooling


def _record_model_result(model: str, ok: bool, error: str = "") -> None:
    with _cooldown_lock:
        if ok:
            _cooldown_until.pop(model, None)
        elif error and not error.startswith("unauthorized"):
            # Model bị gỡ (404) để lâu hơn; lỗi tạm thời thì ngắn
            seconds = LLM_COOLDOWN_SECONDS * (10 if "model_unavailable" in error else 1)
            _cooldown_until[model] = time.time() + seconds


def _log_call(kind: str, model: str, started: float, ok: bool, usage=None, error: str = "", ttft: float | None = None):
    """Một dòng log có cấu trúc cho mỗi lần gọi LLM: nền tảng để quan sát độ trễ/token/lỗi."""
    elapsed_ms = int((time.time() - started) * 1000)
    tokens = ""
    if usage is not None:
        tokens = f" prompt_tokens={getattr(usage, 'prompt_tokens', '?')} completion_tokens={getattr(usage, 'completion_tokens', '?')}"
    ttft_part = f" ttft_ms={int(ttft * 1000)}" if ttft is not None else ""
    level = logging.INFO if ok else logging.WARNING
    logger.log(level, "llm_call kind=%s model=%s ok=%s latency_ms=%d%s%s%s", kind, model, ok, elapsed_ms, ttft_part, tokens, f" error={error}" if error else "")
    _record_model_result(model, ok, error)


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
    max_retries: int | None = None,
) -> tuple[str | None, dict | None]:
    key = _ensure_api_key()
    if not key or not key.strip():
        return None, _build_error_info("missing_api_key")

    models = model_list or OPENROUTER_FALLBACK_MODELS
    retries = LLM_MAX_RETRIES if max_retries is None else max_retries
    last_error = None

    for model_name in _order_models(list(models)):
        started = time.time()
        try:
            request_kwargs = {
                "messages": messages,
                "model": model_name,
                "temperature": temperature,
            }
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens
            _apply_model_options(request_kwargs, model_name)

            completion = _call_openrouter_api(request_kwargs, retries)
            content = completion.choices[0].message.content
            _log_call("chat", model_name, started, True, usage=getattr(completion, "usage", None))
            return (content.strip() if content else ""), None

        except AuthenticationError as error:
            error_info = _build_error_info("unauthorized", str(error), model_name, _status_code_from_error(error))
            _log_call("chat", model_name, started, False, error=error_info["type"])
            return None, error_info

        except RateLimitError as error:
            # Đã hết lượt retry mà vẫn 429 → chuyển sang model tiếp theo
            error_info = _build_error_info("rate_limit", str(error), model_name, 429)
            last_error = error_info
            _log_call("chat", model_name, started, False, error="rate_limit")
            continue

        except APIStatusError as error:
            error_info = _classify_status_error(error, model_name)
            last_error = error_info
            _log_call("chat", model_name, started, False, error=f"{error_info['type']}:{error_info['status_code']}")
            if error_info["type"] in {"unauthorized", "quota_exceeded"}:
                return None, error_info
            continue

        except (APIConnectionError, APITimeoutError) as error:
            error_info = _build_error_info("connection_error", str(error), model_name)
            last_error = error_info
            _log_call("chat", model_name, started, False, error="connection_or_timeout")
            continue

        except Exception as error:
            error_info = _build_error_info("unknown", str(error), model_name)
            last_error = error_info
            _log_call("chat", model_name, started, False, error=f"unknown:{error}")
            continue

    return None, last_error or _build_error_info("unknown")


def call_llm_stream(
    messages: list,
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int | None = None,
):
    """Stream câu trả lời. Nếu một model lỗi TRƯỚC khi phát byte đầu tiên thì thử model kế tiếp."""
    key = _ensure_api_key()
    if not key or not key.strip():
        yield FRIENDLY_ERROR_MESSAGES["missing_api_key"]
        return

    models = list(OPENROUTER_FALLBACK_MODELS)
    if model:
        models = [model] + [m for m in models if m != model]

    last_error = None
    for model_name in _order_models(models):
        started = time.time()
        yielded_any = False
        ttft = None
        try:
            request_kwargs = {
                "messages": messages,
                "model": model_name,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens is not None:
                request_kwargs["max_tokens"] = max_tokens
            _apply_model_options(request_kwargs, model_name)

            stream = _call_openrouter_api_stream(request_kwargs)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    if not yielded_any:
                        ttft = time.time() - started
                    yielded_any = True
                    yield chunk.choices[0].delta.content

            if yielded_any:
                _log_call("stream", model_name, started, True, ttft=ttft)
                return
            # Stream rỗng: coi như model này không trả lời được → thử model sau
            last_error = _build_error_info("unknown", "empty stream", model_name)
            _log_call("stream", model_name, started, False, error="empty_stream")

        except AuthenticationError as error:
            _log_call("stream", model_name, started, False, error="unauthorized")
            yield FRIENDLY_ERROR_MESSAGES["unauthorized"]
            return

        except Exception as error:
            if isinstance(error, APIStatusError):
                last_error = _classify_status_error(error, model_name)
            elif isinstance(error, (APIConnectionError, APITimeoutError)):
                last_error = _build_error_info("connection_error", str(error), model_name)
            else:
                last_error = _build_error_info("unknown", str(error), model_name)
            _log_call("stream", model_name, started, False, error=last_error["type"], ttft=ttft)

            if last_error["type"] in {"unauthorized", "quota_exceeded"}:
                yield last_error["message"]
                return
            if yielded_any:
                # Đã gửi một phần cho người dùng: không thể đổi model giữa chừng.
                yield "\n\n⚠️ Kết nối AI bị gián đoạn trong lúc truyền dữ liệu. Vui lòng thử lại nếu câu trả lời chưa đầy đủ."
                return

    yield (last_error or _build_error_info("unknown"))["message"]
