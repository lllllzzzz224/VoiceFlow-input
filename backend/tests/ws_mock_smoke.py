from __future__ import annotations

import json
import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.contracts import AsrEngine
from app.adapters.faster_whisper import FasterWhisperAdapter
from app.main import app
from app.settings import settings


def assert_standard_result_shape(result: dict) -> None:
    assert "success" in result
    assert "data" in result
    assert "error" in result
    assert "meta" in result


def run_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert_standard_result_shape(payload)
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"


def run_ws_happy_path(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as websocket:
        websocket.send_json(
            {
                "type": "start",
                "sample_rate": 16000,
                "channels": 1,
                "language": "zh",
                "hotwords": ["Kodo"],
            }
        )
        ack = websocket.receive_json()
        assert ack["type"] == "ack"
        assert ack["result"]["success"] is True

        websocket.send_bytes(b"voice")
        websocket.send_json({"type": "end"})
        final_msg = websocket.receive_json()
        assert final_msg["type"] == "transcription_result"

        result = final_msg["result"]
        assert_standard_result_shape(result)
        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["engine"] == "mock"
        assert "mock transcription" in result["data"]["raw_text"]
        assert "final_text" in result["data"]
        assert isinstance(result["data"]["final_text"], str)
        assert result["meta"]["cost_cents"] == 0


def run_ws_no_speech(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as websocket:
        websocket.send_json({"type": "start"})
        _ = websocket.receive_json()
        websocket.send_json({"type": "end"})
        final_msg = websocket.receive_json()
        assert final_msg["type"] == "transcription_result"

        result = final_msg["result"]
        assert_standard_result_shape(result)
        assert result["success"] is False
        assert result["error"]["code"] == "NO_SPEECH_DETECTED"


def run_ws_error_base64(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as websocket:
        websocket.send_json({"type": "start"})
        _ = websocket.receive_json()
        websocket.send_text(json.dumps({"type": "audio_chunk", "chunk_base64": "%%%"}))
        err_msg = websocket.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["result"]["success"] is False
        assert err_msg["result"]["error"]["code"] == "AUDIO_CAPTURE_ERROR"

        websocket.send_json({"type": "end"})
        final_msg = websocket.receive_json()
        assert final_msg["result"]["error"]["code"] == "NO_SPEECH_DETECTED"


def run_ws_error_invalid_json(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as websocket:
        websocket.send_text("{bad-json")
        err_msg = websocket.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["result"]["success"] is False
        assert err_msg["result"]["error"]["code"] == "CONFIG_ERROR"


def run_ws_error_unsupported_type(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as websocket:
        websocket.send_json({"type": "unsupported_event"})
        err_msg = websocket.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["result"]["success"] is False
        assert err_msg["result"]["error"]["code"] == "CONFIG_ERROR"


def run_ws_error_adapter_failure(client: TestClient) -> None:
    previous_engine = settings.asr_engine
    original_get_model = FasterWhisperAdapter._get_model

    def _raise_model_error(self: FasterWhisperAdapter):  # type: ignore[no-untyped-def]
        raise RuntimeError("forced model init failure")

    FasterWhisperAdapter._get_model = _raise_model_error  # type: ignore[assignment]
    settings.asr_engine = AsrEngine.FASTER_WHISPER
    try:
        with client.websocket_connect("/ws/transcribe") as websocket:
            websocket.send_json({"type": "start", "sample_rate": 16000, "channels": 1})
            _ = websocket.receive_json()
            websocket.send_bytes(b"voice")
            websocket.send_json({"type": "end"})
            final_msg = websocket.receive_json()
            assert final_msg["type"] == "transcription_result"
            assert final_msg["result"]["success"] is False
            assert final_msg["result"]["error"]["code"] == "ASR_ENGINE_ERROR"
    finally:
        FasterWhisperAdapter._get_model = original_get_model  # type: ignore[assignment]
        settings.asr_engine = previous_engine


def main() -> None:
    with TestClient(app) as client:
        run_health_check(client)
        run_ws_happy_path(client)
        run_ws_no_speech(client)
        run_ws_error_base64(client)
        run_ws_error_invalid_json(client)
        run_ws_error_unsupported_type(client)
        run_ws_error_adapter_failure(client)
    print("ws_mock_smoke: PASS")


if __name__ == "__main__":
    main()
