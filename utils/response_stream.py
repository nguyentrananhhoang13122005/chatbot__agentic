# -*- coding: utf-8 -*-
"""Chuẩn hoá mọi kiểu phản hồi của agent về một luồng chuỗi để phát SSE.

Agent có thể trả về: str (câu hỏi lại / lỗi), generator[str], hoặc dict có khoá
dataframe / prefix / stream / suffix (nhánh đã kiểm chứng từ DB).
Trước đây SSE lặp trực tiếp qua dict nên người dùng nhận các chunk "dataframe", "prefix", "stream", "suffix".
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator


def iter_response_chunks(response) -> Iterator[str]:
    if response is None:
        return
    if isinstance(response, str):
        if response:
            yield response
        return
    if isinstance(response, dict):
        prefix = response.get("prefix")
        if prefix:
            yield str(prefix)
        stream = response.get("stream")
        if stream is not None:
            yield from iter_response_chunks(stream)
        suffix = response.get("suffix")
        if suffix:
            yield str(suffix)
        return
    if isinstance(response, Iterable):
        for chunk in response:
            if isinstance(chunk, str):
                if chunk:
                    yield chunk
            else:
                yield from iter_response_chunks(chunk)
        return
    yield str(response)
