from __future__ import annotations

import os
import pathlib
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.contracts import AsrEngine
from app.history import history_store
from app.main import app
from app.settings import settings


def main() -> None:
    if os.getenv("RUN_FASTER_WHISPER_TEST", "0").strip() != "1":
        print("faster_whisper_optin_smoke: SKIPPED (set RUN_FASTER_WHISPER_TEST=1 to enable)")
        return

    original_engine = settings.asr_engine
    original_path = history_store.get_path()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_history_file = pathlib.Path(temp_dir) / "history.json"
        history_store.set_path(str(temp_history_file))
        settings.asr_engine = AsrEngine.FASTER_WHISPER
        try:
            with TestClient(app) as client:
                with client.websocket_connect("/ws/transcribe") as ws:
                    ws.send_json({"type": "start", "sample_rate": 16000, "channels": 1, "language": "zh"})
                    _ = ws.receive_json()
                    ws.send_bytes(b"not-real-webm-data")
                    ws.send_json({"type": "end"})
                    msg = ws.receive_json()
                    assert msg["type"] == "transcription_result"
                    result = msg["result"]
                    if result["success"] is True:
                        assert result["data"]["engine"] == "faster_whisper"
                        assert "raw_text" in result["data"]
                        assert "segments" in result["data"]
                        assert "latency_ms" in result["data"]
                    else:
                        assert result["error"]["code"] == "ASR_ENGINE_ERROR"
            print("faster_whisper_optin_smoke: PASS")
        finally:
            settings.asr_engine = original_engine
            history_store.set_path(original_path)


if __name__ == "__main__":
    main()

