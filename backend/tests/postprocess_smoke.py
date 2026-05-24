from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import text_normalizer
from app.postprocess import run_postprocess
from app.settings import settings


HOTWORDS = {
    "github": "GitHub",
    "websocket": "WebSocket",
    "fastapi": "FastAPI",
    "qiniu": "\u4e03\u725b\u4e91",
    "kodo": "Kodo",
    "mcp": "MCP",
}


def test_traditional_to_simplified() -> None:
    raw = "\u505a\u7406\u4e8b\u9084\u662f\u806f\u5408\u5b78"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
        simplified_chinese_enabled=True,
    )
    assert warning is None
    assert final_text == "\u505a\u7406\u4e8b\u8fd8\u662f\u8054\u5408\u5b66\u3002"
    assert corrections == []


def test_meeting_agent_sentence() -> None:
    raw = "\u6703\u8b70\u7d00\u8981 Agent"
    final_text, _corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
        simplified_chinese_enabled=True,
    )
    assert warning is None
    assert final_text == "\u4f1a\u8bae\u7eaa\u8981 Agent\u3002"


def test_case_correction_sentence() -> None:
    raw = "GitHub websocket fastapi"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
        simplified_chinese_enabled=True,
    )
    assert warning is None
    assert final_text == "GitHub WebSocket FastAPI."
    assert any(item.to_text == "WebSocket" for item in corrections)
    assert any(item.to_text == "FastAPI" for item in corrections)


def test_asr_hotwords_merge_for_postprocess() -> None:
    original_asr_hotwords = list(settings.asr_hotwords)
    try:
        settings.asr_hotwords = ["FastAPI", "WebSocket", "GitHub"]
        hotword_map = settings.build_hotword_map_for_session([])
        raw = "github websocket fastapi"
        final_text, _corrections, warning = run_postprocess(
            raw_text=raw,
            hotword_map=hotword_map,
            punctuation_enabled=True,
            spacing_enabled=True,
            simplified_chinese_enabled=True,
        )
        assert warning is None
        assert final_text == "GitHub WebSocket FastAPI."
    finally:
        settings.asr_hotwords = original_asr_hotwords


def test_opencc_and_custom_mapping_sentence() -> None:
    raw = "\u7232\u4e86\u6e2c\u8a66 OpenCC \u88cf\u9762\u7684\u8f49\u63db"
    final_text, _corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
        simplified_chinese_enabled=True,
    )
    assert warning is None
    assert final_text == "\u4e3a\u4e86\u6d4b\u8bd5 OpenCC \u91cc\u9762\u7684\u8f6c\u6362\u3002"


def test_opencc_unavailable_fallback() -> None:
    original_fn = text_normalizer._to_simplified_chinese

    def _raise_error(_text: str) -> str:
        raise RuntimeError("opencc missing")

    text_normalizer._to_simplified_chinese = _raise_error  # type: ignore[assignment]
    try:
        raw = "\u6703\u8b70\u7d00\u8981 Agent"
        final_text, _corrections, warning = run_postprocess(
            raw_text=raw,
            hotword_map=HOTWORDS,
            punctuation_enabled=True,
            spacing_enabled=True,
            simplified_chinese_enabled=True,
        )
        assert final_text == "\u4f1a\u8bae\u7eaa\u8981 Agent\u3002"
        assert warning is not None
        assert warning.startswith("TEXT_NORMALIZER_OPENCC_UNAVAILABLE:")
    finally:
        text_normalizer._to_simplified_chinese = original_fn  # type: ignore[assignment]


def main() -> None:
    test_traditional_to_simplified()
    test_meeting_agent_sentence()
    test_case_correction_sentence()
    test_asr_hotwords_merge_for_postprocess()
    test_opencc_and_custom_mapping_sentence()
    test_opencc_unavailable_fallback()
    print("postprocess_smoke: PASS")


if __name__ == "__main__":
    main()
