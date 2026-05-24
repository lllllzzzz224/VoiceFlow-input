from __future__ import annotations

import base64
import pathlib
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import app.asr_service as asr_service
from app.contracts import AsrEngine
from app.history import history_store
from app.main import app
from app.settings import settings
from app.transcript_state import TranscriptState


def _test_transcript_state_merge() -> None:
    state = TranscriptState()
    assert state.append_partial("我们用 faster") == "我们用 faster"
    assert state.append_partial("faster-whisper 做本地识别") == "我们用 faster-whisper 做本地识别"
    assert state.append_partial("做本地识别") == "我们用 faster-whisper 做本地识别"
    assert state.get_merged_text() == "我们用 faster-whisper 做本地识别"


def _run_disabled_path(client: TestClient) -> None:
    original_enabled = settings.experimental_segment_streaming_enabled
    settings.experimental_segment_streaming_enabled = False
    try:
        with client.websocket_connect("/ws/transcribe") as ws:
            ws.send_json({"type": "start", "streaming_mode": "segment"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["result"]["success"] is False
            assert msg["result"]["error"]["code"] == "CONFIG_ERROR"
    finally:
        settings.experimental_segment_streaming_enabled = original_enabled


def _run_enabled_mock_path(client: TestClient) -> None:
    original_enabled = settings.experimental_segment_streaming_enabled
    original_engine = settings.asr_engine
    settings.experimental_segment_streaming_enabled = True
    settings.asr_engine = AsrEngine.MOCK
    asr_service._ADAPTERS.clear()
    try:
        with client.websocket_connect("/ws/transcribe") as ws:
            ws.send_json(
                {
                    "type": "start",
                    "streaming_mode": "segment",
                    "language": "zh",
                    "asr_mode": "accurate",
                }
            )
            ack = ws.receive_json()
            assert ack["type"] == "ack"
            assert ack["result"]["success"] is True
            assert ack["result"]["data"]["streaming_mode"] == "segment"
            assert ack["result"]["data"]["asr_mode"] == "accurate"

            seg1 = base64.b64encode(b"segment-one").decode("ascii")
            ws.send_json(
                {
                    "type": "audio_segment",
                    "segment_index": 1,
                    "chunk_base64": seg1,
                    "is_final": False,
                }
            )
            partial = ws.receive_json()
            assert partial["type"] == "partial_transcription_result"
            assert partial["result"]["success"] is True
            partial_data = partial["result"]["data"]
            partial_meta = partial["result"]["meta"]
            assert partial_data["segment_index"] == 1
            assert partial_data["is_final"] is False
            assert partial_data["engine"] == "mock"
            assert isinstance(partial_data["partial_text"], str) and partial_data["partial_text"]
            assert isinstance(partial_data["merged_text"], str) and partial_data["merged_text"]
            assert "decode_ms" in partial_meta
            assert "asr_ms" in partial_meta
            assert "postprocess_ms" in partial_meta
            assert "total_ms" in partial_meta
            assert "audio_quality" in partial_meta
            assert partial_meta["asr_mode"] == "accurate"
            assert partial_meta["model"] == settings.asr_accurate_model

            ws.send_json({"type": "end"})
            final_msg = ws.receive_json()
            assert final_msg["type"] == "transcription_result"
            final_result = final_msg["result"]
            assert final_result["success"] is True
            assert isinstance(final_result["data"]["final_text"], str)
            assert final_result["data"]["engine"] == "mock"
            assert final_result["meta"]["asr_mode"] == "accurate"
            assert final_result["meta"]["model"] == settings.asr_accurate_model
            assert "decode_ms" in final_result["meta"]
            assert "asr_ms" in final_result["meta"]
            assert "postprocess_ms" in final_result["meta"]
            assert "total_ms" in final_result["meta"]

        history_payload = client.get("/history").json()
        assert history_payload["success"] is True
        assert history_payload["data"]["count"] == 1
        assert history_payload["data"]["items"][0]["success"] is True
    finally:
        settings.experimental_segment_streaming_enabled = original_enabled
        settings.asr_engine = original_engine
        asr_service._ADAPTERS.clear()


def _run_partial_error_path(client: TestClient) -> None:
    original_enabled = settings.experimental_segment_streaming_enabled
    original_engine = settings.asr_engine
    settings.experimental_segment_streaming_enabled = True
    settings.asr_engine = AsrEngine.MOCK
    asr_service._ADAPTERS.clear()
    try:
        with client.websocket_connect("/ws/transcribe") as ws:
            ws.send_json({"type": "start", "streaming_mode": "segment"})
            _ = ws.receive_json()
            ws.send_json({"type": "audio_segment", "segment_index": 1, "chunk_base64": "%%%bad"})
            partial_error = ws.receive_json()
            assert partial_error["type"] == "partial_error"
            assert partial_error["result"]["success"] is False
            assert partial_error["result"]["error"]["code"] == "AUDIO_CAPTURE_ERROR"

            ws.send_json({"type": "end"})
            final_msg = ws.receive_json()
            assert final_msg["type"] == "transcription_result"
            assert final_msg["result"]["success"] is False
            assert final_msg["result"]["error"]["code"] == "NO_SPEECH_DETECTED"
    finally:
        settings.experimental_segment_streaming_enabled = original_enabled
        settings.asr_engine = original_engine
        asr_service._ADAPTERS.clear()


def main() -> None:
    _test_transcript_state_merge()
    original_history_path = history_store.get_path()
    with tempfile.TemporaryDirectory() as temp_dir:
        history_store.set_path(str(pathlib.Path(temp_dir) / "history.json"))
        try:
            with TestClient(app) as client:
                client.delete("/history")
                _run_disabled_path(client)
                client.delete("/history")
                _run_enabled_mock_path(client)
                client.delete("/history")
                _run_partial_error_path(client)
        finally:
            history_store.set_path(original_history_path)
    print("segment_streaming_smoke: PASS")


if __name__ == "__main__":
    main()
