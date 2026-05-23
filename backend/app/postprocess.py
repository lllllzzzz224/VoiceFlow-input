from __future__ import annotations

import re

from app.contracts import AppliedCorrection

_CJK_BLOCK = r"\u4e00-\u9fff"


def _normalize_spacing(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return cleaned
    cleaned = re.sub(rf"([{_CJK_BLOCK}])\s+([{_CJK_BLOCK}])", r"\1\2", cleaned)
    cleaned = re.sub(rf"([{_CJK_BLOCK}])([A-Za-z0-9])", r"\1 \2", cleaned)
    cleaned = re.sub(rf"([A-Za-z0-9])([{_CJK_BLOCK}])", r"\1 \2", cleaned)
    return cleaned.strip()


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
    if text[-1] in "。！？.!?":
        return text
    return f"{text}。"


def run_postprocess(
    raw_text: str,
    hotword_map: dict[str, str],
    punctuation_enabled: bool = True,
    spacing_enabled: bool = True,
) -> tuple[str, list[AppliedCorrection], str | None]:
    try:
        working = raw_text or ""
        if spacing_enabled:
            working = _normalize_spacing(working)
        working, corrections = _apply_hotwords(working, hotword_map)
        if punctuation_enabled:
            working = _append_punctuation(working)
        return working, corrections, None
    except Exception as exc:
        return raw_text, [], f"POSTPROCESS_ERROR: {exc}"

