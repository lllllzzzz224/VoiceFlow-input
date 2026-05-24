from __future__ import annotations

import json
import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.contracts import AsrEngine
from app.adapters.faster_whisper import AsrProcessingError, FasterWhisperAdapter
from app.adapters.base import TranscriptionInput
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
    assert payload["meta"]["asr_modes"]["fast"] == settings.asr_fast_model
    assert payload["meta"]["asr_modes"]["accurate"] == settings.asr_accurate_model


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
        assert "bytes_received" in result["meta"]
        assert "decode_ms" in result["meta"]
        assert "asr_ms" in result["meta"]
        assert "postprocess_ms" in result["meta"]
        assert "total_ms" in result["meta"]
        assert "audio_duration_ms" in result["meta"]
        assert "model_cached" in result["meta"]
        assert "model" in result["meta"]
        assert result["meta"]["asr_mode"] == "fast"
        assert "hotwords_enabled" in result["meta"]
        assert "hotwords_count" in result["meta"]
        assert result["meta"]["cost_cents"] == 0


def run_ws_accurate_mode(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as websocket:
        websocket.send_json(
            {
                "type": "start",
                "sample_rate": 16000,
                "channels": 1,
                "language": "zh",
                "asr_mode": "accurate",
            }
        )
        ack = websocket.receive_json()
        assert ack["type"] == "ack"
        assert ack["result"]["success"] is True
        assert ack["result"]["data"]["asr_mode"] == "accurate"

        websocket.send_bytes(b"voice")
        websocket.send_json({"type": "end"})
        final_msg = websocket.receive_json()
        result = final_msg["result"]
        assert result["success"] is True
        assert result["meta"]["asr_mode"] == "accurate"
        assert result["meta"]["model"] == settings.asr_accurate_model


def run_faster_whisper_model_resolver() -> None:
    adapter = FasterWhisperAdapter()

    model, mode = adapter._resolve_model_name(
        TranscriptionInput(audio_bytes=b"x", asr_mode="fast", asr_mode_provided=True)
    )
    assert model == settings.asr_fast_model
    assert mode == "fast"

    model, mode = adapter._resolve_model_name(
        TranscriptionInput(audio_bytes=b"x", asr_mode="accurate", asr_mode_provided=True)
    )
    assert model == settings.asr_accurate_model
    assert mode == "accurate"


def run_hotwords_config_behavior(client: TestClient) -> None:
    original_asr_hotwords = list(settings.asr_hotwords)
    try:
        settings.asr_hotwords = ["FastAPI", "WebSocket", "GitHub"]
        prompt = settings.build_initial_prompt([])
        assert isinstance(prompt, str) and "FastAPI" in prompt and "WebSocket" in prompt and "GitHub" in prompt
        with client.websocket_connect("/ws/transcribe") as websocket:
            websocket.send_json({"type": "start", "sample_rate": 16000, "channels": 1, "language": "zh"})
            _ = websocket.receive_json()
            websocket.send_bytes(b"voice")
            websocket.send_json({"type": "end"})
            final_msg = websocket.receive_json()
            assert final_msg["type"] == "transcription_result"
            result = final_msg["result"]
            assert result["success"] is True
            assert result["meta"]["hotwords_enabled"] is True
            assert result["meta"]["hotwords_count"] == 3
    finally:
        settings.asr_hotwords = original_asr_hotwords


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

    def _raise_model_error(self: FasterWhisperAdapter, _payload):  # type: ignore[no-untyped-def]
        raise AsrProcessingError("model_load_failed", "forced model init failure")

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
            assert final_msg["result"]["error"]["details"]["reason"] == "model_load_failed"
    finally:
        FasterWhisperAdapter._get_model = original_get_model  # type: ignore[assignment]
        settings.asr_engine = previous_engine


def run_ws_error_audio_too_large(client: TestClient) -> None:
    previous_limit = settings.max_audio_bytes
    settings.max_audio_bytes = 8
    try:
        with client.websocket_connect("/ws/transcribe") as websocket:
            websocket.send_json({"type": "start", "sample_rate": 16000, "channels": 1})
            _ = websocket.receive_json()
            websocket.send_bytes(b"0123456789")
            final_msg = websocket.receive_json()
            assert final_msg["type"] == "transcription_result"
            assert final_msg["result"]["success"] is False
            assert final_msg["result"]["error"]["code"] == "AUDIO_TOO_LARGE"
    finally:
        settings.max_audio_bytes = previous_limit


def run_ws_error_audio_too_long(client: TestClient) -> None:
    previous_engine = settings.asr_engine
    original_get_model = FasterWhisperAdapter._get_model
    original_decode = FasterWhisperAdapter._transcribe_sync

    class _FakeModel:
        def transcribe(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            return iter([]), None

    def _fake_get_model(self: FasterWhisperAdapter, _payload):  # type: ignore[no-untyped-def]
        return _FakeModel(), True, settings.asr_fast_model, "fast"

    def _raise_too_long(self: FasterWhisperAdapter, _payload):  # type: ignore[no-untyped-def]
        raise AsrProcessingError(
            "audio_too_long",
            "Audio duration exceeds configured limit.",
            {"audio_duration_ms": 35000, "max_recording_seconds": 30},
        )

    FasterWhisperAdapter._get_model = _fake_get_model  # type: ignore[assignment]
    FasterWhisperAdapter._transcribe_sync = _raise_too_long  # type: ignore[assignment]
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
            assert final_msg["result"]["error"]["code"] == "CONFIG_ERROR"
            assert final_msg["result"]["error"]["details"]["reason"] == "audio_too_long"
    finally:
        FasterWhisperAdapter._get_model = original_get_model  # type: ignore[assignment]
        FasterWhisperAdapter._transcribe_sync = original_decode  # type: ignore[assignment]
        settings.asr_engine = previous_engine


def main() -> None:
    run_faster_whisper_model_resolver()
    with TestClient(app) as client:
        run_health_check(client)
        run_ws_happy_path(client)
        run_hotwords_config_behavior(client)
        run_ws_accurate_mode(client)
        run_ws_no_speech(client)
        run_ws_error_base64(client)
        run_ws_error_invalid_json(client)
        run_ws_error_unsupported_type(client)
        run_ws_error_adapter_failure(client)
        run_ws_error_audio_too_large(client)
        run_ws_error_audio_too_long(client)
    print("ws_mock_smoke: PASS")


if __name__ == "__main__":
    main()
