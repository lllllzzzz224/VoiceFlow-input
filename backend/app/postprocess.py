from __future__ import annotations

import re

from app.contracts import AppliedCorrection

_CJK_BLOCK = r"\u4e00-\u9fff"
_SENTENCE_ENDINGS = "。！？!?;；."
_COMMON_CASE_MAP = {
    "github": "GitHub",
    "websocket": "WebSocket",
    "fastapi": "FastAPI",
    "faster whisper": "faster-whisper",
    "faster-whisper": "faster-whisper",
    "kodo": "Kodo",
    "mcp": "MCP",
}


def _to_simplified_chinese(text: str) -> str:
    from opencc import OpenCC

    converter = OpenCC("t2s")
    return converter.convert(text)


def _normalize_spacing(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return cleaned
    cleaned = re.sub(r"\s+([,.;!?，。！？；：])", r"\1", cleaned)
    cleaned = re.sub(rf"([{_CJK_BLOCK}])\s+([{_CJK_BLOCK}])", r"\1\2", cleaned)
    cleaned = re.sub(rf"([{_CJK_BLOCK}])([A-Za-z0-9])", r"\1 \2", cleaned)
    cleaned = re.sub(rf"([A-Za-z0-9])([{_CJK_BLOCK}])", r"\1 \2", cleaned)
    return cleaned.strip()


def _apply_common_case_corrections(text: str) -> tuple[str, list[AppliedCorrection]]:
    result = text
    applied: list[AppliedCorrection] = []
    for source, target in _COMMON_CASE_MAP.items():
        pattern = re.compile(rf"(?<![A-Za-z0-9-]){re.escape(source)}(?![A-Za-z0-9-])", flags=re.IGNORECASE)
        if pattern.search(result) is None:
            continue
        result = pattern.sub(target, result)
        applied.append(AppliedCorrection(from_text=source, to_text=target, correction_type="case"))
    return result, applied


def _apply_hotwords(text: str, hotword_map: dict[str, str]) -> tuple[str, list[AppliedCorrection]]:
    result = text
    applied: list[AppliedCorrection] = []
    for source, target in hotword_map.items():
        if not source:
            continue
        pattern = re.compile(re.escape(source), flags=re.IGNORECASE)
        if pattern.search(result) is None:
            continue
        result = pattern.sub(target, result)
        applied.append(AppliedCorrection(from_text=source, to_text=target, correction_type="hotword"))
    return result, applied


def _append_punctuation(text: str) -> str:
    if not text:
        return text
    if text[-1] in _SENTENCE_ENDINGS:
        if re.search(rf"[{_CJK_BLOCK}]", text):
            return text[:-1] + "。" if text[-1] == "." else text
        return text
    if re.search(rf"[{_CJK_BLOCK}]", text):
        return f"{text}。"
    return f"{text}."


def run_postprocess(
    raw_text: str,
    hotword_map: dict[str, str],
    punctuation_enabled: bool = True,
    spacing_enabled: bool = True,
    simplified_chinese_enabled: bool = True,
) -> tuple[str, list[AppliedCorrection], str | None]:
    try:
        working = raw_text or ""
        warning: str | None = None

        if simplified_chinese_enabled and working:
            try:
                working = _to_simplified_chinese(working)
            except Exception as exc:
                warning = f"POSTPROCESS_SIMPLIFIED_CHINESE_UNAVAILABLE: {exc}"

        if spacing_enabled:
            working = _normalize_spacing(working)

        corrections: list[AppliedCorrection] = []
        working, case_corrections = _apply_common_case_corrections(working)
        corrections.extend(case_corrections)
        working, hotword_corrections = _apply_hotwords(working, hotword_map)
        corrections.extend(hotword_corrections)

        if punctuation_enabled:
            working = _append_punctuation(working)

        return working, corrections, warning
    except Exception as exc:
        return raw_text, [], f"POSTPROCESS_ERROR: {exc}"
