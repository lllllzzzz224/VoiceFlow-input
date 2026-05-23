from __future__ import annotations

import argparse
import asyncio
import json
import urllib.request
from urllib.parse import urlparse

import websockets


def assert_standard_result_shape(result: dict) -> None:
    assert "success" in result
    assert "data" in result
    assert "error" in result
    assert "meta" in result


def build_ws_url(base_http_url: str) -> str:
    parsed = urlparse(base_http_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/ws/transcribe"


def check_health(base_http_url: str) -> None:
    with urllib.request.urlopen(f"{base_http_url}/health", timeout=10) as response:
        assert response.status == 200
        payload = json.loads(response.read().decode("utf-8"))
    assert_standard_result_shape(payload)
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    print("health: PASS")


async def check_happy_path(ws_url: str) -> None:
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "start", "sample_rate": 16000, "channels": 1}))
        ack = json.loads(await ws.recv())
        assert ack["type"] == "ack"
        assert ack["result"]["success"] is True

        await ws.send(b"voice")
        await ws.send(json.dumps({"type": "end"}))
        final_msg = json.loads(await ws.recv())
        assert final_msg["type"] == "transcription_result"
        result = final_msg["result"]
        assert_standard_result_shape(result)
        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["engine"] == "mock"
        assert "mock transcription" in result["data"]["raw_text"]
        assert "final_text" in result["data"]
        assert isinstance(result["data"]["final_text"], str)
    print("ws happy-path: PASS")


async def check_no_speech(ws_url: str) -> None:
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "start"}))
        _ = await ws.recv()
        await ws.send(json.dumps({"type": "end"}))
        final_msg = json.loads(await ws.recv())
        assert final_msg["type"] == "transcription_result"
        result = final_msg["result"]
        assert_standard_result_shape(result)
        assert result["success"] is False
        assert result["error"]["code"] == "NO_SPEECH_DETECTED"
    print("ws no-speech: PASS")


async def check_invalid_base64(ws_url: str) -> None:
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "start"}))
        _ = await ws.recv()
        await ws.send(json.dumps({"type": "audio_chunk", "chunk_base64": "%%%"}))
        error_msg = json.loads(await ws.recv())
        assert error_msg["type"] == "error"
        assert error_msg["result"]["success"] is False
        assert error_msg["result"]["error"]["code"] == "AUDIO_CAPTURE_ERROR"

        await ws.send(json.dumps({"type": "end"}))
        final_msg = json.loads(await ws.recv())
        assert final_msg["result"]["success"] is False
        assert final_msg["result"]["error"]["code"] == "NO_SPEECH_DETECTED"
    print("ws invalid-base64: PASS")


async def check_invalid_json(ws_url: str) -> None:
    async with websockets.connect(ws_url) as ws:
        await ws.send("{bad-json")
        err_msg = json.loads(await ws.recv())
        assert err_msg["type"] == "error"
        assert err_msg["result"]["success"] is False
        assert err_msg["result"]["error"]["code"] == "CONFIG_ERROR"
    print("ws invalid-json: PASS")


async def check_unsupported_type(ws_url: str) -> None:
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "unsupported_event"}))
        err_msg = json.loads(await ws.recv())
        assert err_msg["type"] == "error"
        assert err_msg["result"]["success"] is False
        assert err_msg["result"]["error"]["code"] == "CONFIG_ERROR"
    print("ws unsupported-type: PASS")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Live WebSocket mock checks for VoiceFlow backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base HTTP URL, e.g. http://127.0.0.1:8000")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    ws_url = build_ws_url(base_url)

    check_health(base_url)
    await check_happy_path(ws_url)
    await check_no_speech(ws_url)
    await check_invalid_base64(ws_url)
    await check_invalid_json(ws_url)
    await check_unsupported_type(ws_url)
    print("ws_live_mock_checks: PASS")


if __name__ == "__main__":
    asyncio.run(main())
