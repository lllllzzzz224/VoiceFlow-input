from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import urlparse

import websockets


def build_ws_url(base_http_url: str) -> str:
    parsed = urlparse(base_http_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/ws/transcribe"


async def run_one_session(ws_url: str, index: int) -> None:
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"type": "start", "sample_rate": 16000, "channels": 1}))
        ack = json.loads(await ws.recv())
        assert ack["type"] == "ack"
        assert ack["result"]["success"] is True

        await ws.send(f"voice-{index}".encode("utf-8"))
        await ws.send(json.dumps({"type": "end"}))
        final_msg = json.loads(await ws.recv())
        assert final_msg["type"] == "transcription_result"
        result = final_msg["result"]
        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["engine"] == "mock"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Live WebSocket concurrency smoke test for VoiceFlow backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base HTTP URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--sessions", type=int, default=3, help="Concurrent websocket sessions (2-5 recommended).")
    args = parser.parse_args()

    if args.sessions < 2 or args.sessions > 5:
        raise ValueError("--sessions must be between 2 and 5.")

    ws_url = build_ws_url(args.base_url.rstrip("/"))
    tasks = [run_one_session(ws_url, idx) for idx in range(args.sessions)]
    await asyncio.gather(*tasks)
    print(f"ws_live_concurrency_smoke: PASS ({args.sessions} sessions)")


if __name__ == "__main__":
    asyncio.run(main())

