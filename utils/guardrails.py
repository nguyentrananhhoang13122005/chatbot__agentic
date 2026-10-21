# -*- coding: utf-8 -*-
"""
Guardrails đầu vào cho chatbot (Day 11: input rails).

Có 3 lớp, tất cả bằng CODE chứ không chỉ dặn trong prompt ("một luật chỉ nằm trong system prompt
không phải là một lớp phòng thủ"):
  1. Validation   : rỗng, quá dài, ký tự điều khiển.
  2. Injection    : mẫu regex cho tiếng Anh VÀ tiếng Việt (người dùng của hệ thống nói tiếng Việt).
  3. Rate limit   : cửa sổ trượt theo người dùng/IP để chặn spam và đội chi phí LLM.

Regex chỉ bắt được các kiểu tấn công phổ biến (~60-70% theo tài liệu Day 11), nên đây là lớp rẻ
đứng TRƯỚC; phần còn lại dựa vào việc bot chỉ ĐỌC dữ liệu và không có tool nguy hiểm.
"""
from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from collections import defaultdict, deque

MAX_QUERY_CHARS = int(os.getenv("MAX_QUERY_CHARS", "1000"))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS = 800

INJECTION_PATTERNS = [
    # Tiếng Anh
    r"ignore (all )?(the )?(previous|above|prior) (instructions|prompts?|rules)",
    r"disregard (all )?(the )?(previous|above|prior)",
    r"you are now\b",
    r"\bdan\b.{0,20}(do anything|no (rules|limits))",
    r"(reveal|show|print|repeat|leak).{0,25}(system prompt|instructions|your prompt)",
    r"system prompt",
    r"developer mode",
    # Tiếng Việt (có dấu và không dấu)
    r"b[oỏ] qua (t[aấ]t c[aả] |m[oọ]i |to[aà]n b[oộ] )?(c[aá]c )?(h[uư][oớ]ng d[aẫ]n|ch[iỉ] d[aẫ]n|quy t[aắ]c|lu[aậ]t)",
    r"qu[eê]n (h[eế]t |t[aấ]t c[aả] |m[oọ]i )?(c[aá]c )?(h[uư][oớ]ng d[aẫ]n|quy t[aắ]c|lu[aậ]t)",
    r"(ti[eế]t l[oộ]|cho (t[oô]i )?xem|in ra|l[aặ]p l[aạ]i).{0,25}(system prompt|prompt h[eệ] th[oố]ng|h[uư][oớ]ng d[aẫ]n h[eệ] th[oố]ng|api key|kh[oó]a api)",
    r"t[uừ] gi[oờ] (b[aạ]n|m[aà]y|em) l[aà]",
    r"(gi[aả] v[oờ]|đ[oó]ng vai).{0,30}(kh[oô]ng c[oó] (gi[oớ]i h[aạ]n|quy t[aắ]c))",
    r"bo qua (cac )?(huong dan|chi dan|quy tac)",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class GuardrailViolation(Exception):
    """Đầu vào bị chặn. `code` để log/đo, `message` là câu thân thiện hiển thị cho người dùng."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def sanitize_text(text: str) -> str:
    """NFC + bỏ ký tự điều khiển + gọn khoảng trắng."""
    cleaned = unicodedata.normalize("NFC", text or "")
    cleaned = _CONTROL_CHARS.sub(" ", cleaned)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def detect_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in _INJECTION_RE)


def validate_user_query(text: str) -> str:
    """Trả về câu hỏi đã làm sạch hoặc ném GuardrailViolation."""
    cleaned = sanitize_text(text)
    if not cleaned:
        raise GuardrailViolation("empty", "Bạn chưa nhập câu hỏi. Hãy hỏi về điểm chuẩn, ngành học hoặc phương thức xét tuyển nhé!")
    if len(cleaned) > MAX_QUERY_CHARS:
        raise GuardrailViolation(
            "too_long",
            f"Câu hỏi quá dài (tối đa {MAX_QUERY_CHARS} ký tự). Bạn hãy rút gọn lại giúp mình nhé.",
        )
    if detect_injection(cleaned):
        raise GuardrailViolation(
            "injection",
            "Mình chỉ hỗ trợ tư vấn tuyển sinh đại học và không thể thực hiện yêu cầu thay đổi/tiết lộ cách hoạt động của hệ thống. "
            "Bạn có thể hỏi về điểm chuẩn, ngành học hay phương thức xét tuyển.",
        )
    return cleaned


def sanitize_history(history) -> list[dict]:
    """Chỉ giữ vai trò user/assistant hợp lệ, cắt ngắn, lấy vài lượt gần nhất (sliding window)."""
    cleaned: list[dict] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = sanitize_text(str(item.get("content", "")))
        if role not in {"user", "assistant"} or not content:
            continue
        cleaned.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return cleaned[-MAX_HISTORY_MESSAGES:]


class SlidingWindowRateLimiter:
    """Giới hạn số request theo khoá (user id / IP) trong một cửa sổ thời gian. Lưu trong bộ nhớ tiến trình."""

    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise GuardrailViolation(
                    "rate_limited",
                    f"Bạn gửi câu hỏi hơi nhanh. Vui lòng thử lại sau khoảng {retry_after} giây.",
                    status_code=429,
                )
            hits.append(now)


chat_rate_limiter = SlidingWindowRateLimiter()
