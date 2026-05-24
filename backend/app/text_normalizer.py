from __future__ import annotations

import re
import unicodedata

from app.contracts import AppliedCorrection

_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_END_PUNCTUATION = {".", "!", "?", "。", "！", "？"}

_CUSTOM_CHAR_MAP = {
    "\u88cf": "\u91cc",  # 裏 -> 里
    "\u88e1": "\u91cc",  # 裡 -> 里
    "\u7232": "\u4e3a",  # 爲 -> 为
    "\u70ba": "\u4e3a",  # 為 -> 为
    "\u7e94": "\u624d",  # 纔 -> 才
    "\u8457": "\u7740",  # 著 -> 着
    "\u6703": "\u4f1a",  # 會 -> 会
    "\u8b70": "\u8bae",  # 議 -> 议
    "\u7d00": "\u7eaa",  # 紀 -> 纪
    "\u9304": "\u5f55",  # 錄 -> 录
    "\u806f": "\u8054",  # 聯 -> 联
    "\u5b78": "\u5b66",  # 學 -> 学
    "\u8aaa": "\u8bf4",  # 說 -> 说
    "\u8a71": "\u8bdd",  # 話 -> 话
    "\u8a9e": "\u8bed",  # 語 -> 语
    "\u807d": "\u542c",  # 聽 -> 听
    "\u5beb": "\u5199",  # 寫 -> 写
    "\u8f49": "\u8f6c",  # 轉 -> 转
    "\u8b58": "\u8bc6",  # 識 -> 识
    "\u5225": "\u522b",  # 別 -> 别
    "\u6e2c": "\u6d4b",  # 測 -> 测
    "\u8a66": "\u8bd5",  # 試 -> 试
    "\u958b": "\u5f00",  # 開 -> 开
    "\u767c": "\u53d1",  # 發 -> 发
    "\u96f2": "\u4e91",  # 雲 -> 云
    "\u5132": "\u50a8",  # 儲 -> 储
    "\u52d9": "\u52a1",  # 務 -> 务
}

_PUNCT_TRANSLATION = str.maketrans(
    {
        "\uff0c": ",",
        "\u3002": ".",
        "\uff01": "!",
        "\uff1f": "?",
        "\uff1b": ";",
        "\uff1a": ":",
        "\u3001": ",",
        "\uff08": "(",
        "\uff09": ")",
        "\u3010": "[",
        "\u3011": "]",
        "\u300c": '"',
        "\u300d": '"',
        "\u300e": '"',
        "\u300f": '"',
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2014": "-",
        "\u2013": "-",
        "\uff5e": "~",
    }
)

_COMMON_CASE_MAP = {
    "github": "GitHub",
    "websocket": "WebSocket",
    "fastapi": "FastAPI",
    "opencc": "OpenCC",
    "faster whisper": "faster-whisper",
    "faster-whisper": "faster-whisper",
    "kodo": "Kodo",
    "mcp": "MCP",
}


def _to_simplified_chinese(text: str) -> str:
    from opencc import OpenCC

    converter = OpenCC("t2s")
    return converter.convert(text)


def _contains_cjk(text: str) -> bool:
    return _CJK_PATTERN.search(text) is not None


def _apply_custom_map(text: str) -> str:
    result = text
    for source, target in _CUSTOM_CHAR_MAP.items():
        result = result.replace(source, target)
    return result


def _normalize_punctuation(text: str) -> str:
    result = text.translate(_PUNCT_TRANSLATION)
    result = re.sub(r"\s+([,.;:!?])", r"\1", result)
    result = re.sub(r"([(\[])\s+", r"\1", result)
    result = re.sub(r"\s+([)\]])", r"\1", result)
    return result


def _normalize_spacing(text: str) -> str:
    result = re.sub(r"\s+", " ", text).strip()
    if not result:
        return result
    result = re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", result)
    result = re.sub(r"([\u4e00-\u9fff])([A-Za-z0-9])", r"\1 \2", result)
    result = re.sub(r"([A-Za-z0-9])([\u4e00-\u9fff])", r"\1 \2", result)
    result = re.sub(r"\s+([,.;:!?])", r"\1", result)
    result = re.sub(r"([,.;:!?])([A-Za-z0-9])", r"\1 \2", result)
    return result.strip()


def _apply_case_corrections(text: str) -> tuple[str, list[AppliedCorrection]]:
    result = text
    applied: list[AppliedCorrection] = []
    for source, target in _COMMON_CASE_MAP.items():
        pattern = re.compile(rf"(?<![A-Za-z0-9-]){re.escape(source)}(?![A-Za-z0-9-])", re.IGNORECASE)
        if pattern.search(result) is None:
            continue
        result = pattern.sub(target, result)
        applied.append(AppliedCorrection(from_text=source, to_text=target, correction_type="case"))
    return result, applied


def _apply_hotword_corrections(text: str, hotword_map: dict[str, str]) -> tuple[str, list[AppliedCorrection]]:
    result = text
    applied: list[AppliedCorrection] = []
    for source, target in hotword_map.items():
        source_norm = (source or "").strip()
        target_norm = (target or "").strip()
        if not source_norm or not target_norm:
            continue
        pattern = re.compile(re.escape(source_norm), re.IGNORECASE)
        if pattern.search(result) is None:
            continue
        result = pattern.sub(target_norm, result)
        applied.append(AppliedCorrection(from_text=source_norm, to_text=target_norm, correction_type="hotword"))
    return result, applied


def _append_sentence_ending(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return normalized
    has_cjk = _contains_cjk(normalized)
    last_char = normalized[-1]
    if last_char in _END_PUNCTUATION:
        if has_cjk and last_char == ".":
            return normalized[:-1] + "。"
        if has_cjk and last_char == "!":
            return normalized[:-1] + "！"
        if has_cjk and last_char == "?":
            return normalized[:-1] + "？"
        return normalized
    return f"{normalized}。" if has_cjk else f"{normalized}."


def normalize_text(
    text: str,
    hotword_map: dict[str, str],
    punctuation_enabled: bool = True,
    spacing_enabled: bool = True,
    simplified_chinese_enabled: bool = True,
) -> tuple[str, list[AppliedCorrection], str | None]:
    try:
        working = unicodedata.normalize("NFKC", text or "")
        warning: str | None = None
        corrections: list[AppliedCorrection] = []

        if simplified_chinese_enabled and working:
            try:
                working = _to_simplified_chinese(working)
            except Exception as exc:
                warning = f"TEXT_NORMALIZER_OPENCC_UNAVAILABLE: {exc}"

        working = _apply_custom_map(working)
        if punctuation_enabled:
            working = _normalize_punctuation(working)
        if spacing_enabled:
            working = _normalize_spacing(working)

        working, case_corrections = _apply_case_corrections(working)
        corrections.extend(case_corrections)
        working, hotword_corrections = _apply_hotword_corrections(working, hotword_map)
        corrections.extend(hotword_corrections)

        if punctuation_enabled:
            working = _append_sentence_ending(working)
        return working, corrections, warning
    except Exception as exc:
        return text, [], f"TEXT_NORMALIZER_ERROR: {exc}"
