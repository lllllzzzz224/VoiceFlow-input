from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.postprocess import run_postprocess


HOTWORDS = {
    "github": "GitHub",
    "websocket": "WebSocket",
    "fastapi": "FastAPI",
}


def test_traditional_to_simplified() -> None:
    raw = "做理事還是聯合學"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
        simplified_chinese_enabled=True,
    )
    assert warning is None
    assert final_text == "做理事还是联合学。"
    assert corrections == []


def test_meeting_agent_sentence() -> None:
    raw = "會議紀要 Agent"
    final_text, _corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
        simplified_chinese_enabled=True,
    )
    assert warning is None
    assert final_text == "会议纪要 Agent。"


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


def test_opencc_unavailable_fallback() -> None:
    import app.postprocess as postprocess

    original_fn = postprocess._to_simplified_chinese

    def _raise_error(_text: str) -> str:
        raise RuntimeError("opencc missing")

    postprocess._to_simplified_chinese = _raise_error  # type: ignore[assignment]
    try:
        raw = "會議紀要 Agent"
        final_text, _corrections, warning = run_postprocess(
            raw_text=raw,
            hotword_map=HOTWORDS,
            punctuation_enabled=True,
            spacing_enabled=True,
            simplified_chinese_enabled=True,
        )
        assert final_text == "會議紀要 Agent。"
        assert warning is not None and warning.startswith("POSTPROCESS_SIMPLIFIED_CHINESE_UNAVAILABLE:")
    finally:
        postprocess._to_simplified_chinese = original_fn  # type: ignore[assignment]


def main() -> None:
    test_traditional_to_simplified()
    test_meeting_agent_sentence()
    test_case_correction_sentence()
    test_opencc_unavailable_fallback()
    print("postprocess_smoke: PASS")


if __name__ == "__main__":
    main()
