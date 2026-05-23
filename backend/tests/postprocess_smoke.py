from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.postprocess import run_postprocess


HOTWORDS = {
    "七牛云": "七牛云",
    "kodo": "Kodo",
    "mcp": "MCP",
    "github": "GitHub",
    "fastapi": "FastAPI",
    "faster whisper": "faster-whisper",
    "websocket": "WebSocket",
}


def test_sentence_qiniu_kodo() -> None:
    raw = "七牛云 kodo 存储"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
    )
    assert warning is None
    assert final_text == "七牛云 Kodo 存储。"
    assert any(item.to_text == "Kodo" for item in corrections)


def test_sentence_fastapi_websocket() -> None:
    raw = "这个项目使用 fastapi 和 websocket"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
    )
    assert warning is None
    assert final_text == "这个项目使用 FastAPI 和 WebSocket。"
    assert any(item.to_text == "FastAPI" for item in corrections)
    assert any(item.to_text == "WebSocket" for item in corrections)


def test_sentence_faster_whisper() -> None:
    raw = "我们用 faster whisper 做本地识别"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=HOTWORDS,
        punctuation_enabled=True,
        spacing_enabled=True,
    )
    assert warning is None
    assert final_text == "我们用 faster-whisper 做本地识别。"
    assert any(item.to_text == "faster-whisper" for item in corrections)


def test_failure_fallback() -> None:
    raw = "hello world"
    final_text, corrections, warning = run_postprocess(
        raw_text=raw,
        hotword_map=None,  # type: ignore[arg-type]
        punctuation_enabled=True,
        spacing_enabled=True,
    )
    assert final_text == raw
    assert corrections == []
    assert warning is not None and warning.startswith("POSTPROCESS_ERROR:")


def main() -> None:
    test_sentence_qiniu_kodo()
    test_sentence_fastapi_websocket()
    test_sentence_faster_whisper()
    test_failure_fallback()
    print("postprocess_smoke: PASS")


if __name__ == "__main__":
    main()
