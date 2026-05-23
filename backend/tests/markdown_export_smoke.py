from __future__ import annotations

import pathlib
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.history import history_store
from app.main import app


def _create_success_item(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as ws:
        ws.send_json({"type": "start", "sample_rate": 16000, "channels": 1})
        _ = ws.receive_json()
        ws.send_bytes(b"voice")
        ws.send_json({"type": "end"})
        msg = ws.receive_json()
        assert msg["result"]["success"] is True


def _create_failure_item(client: TestClient) -> None:
    with client.websocket_connect("/ws/transcribe") as ws:
        ws.send_json({"type": "start"})
        _ = ws.receive_json()
        ws.send_json({"type": "end"})
        msg = ws.receive_json()
        assert msg["result"]["success"] is False
        assert msg["result"]["error"]["code"] == "NO_SPEECH_DETECTED"


def main() -> None:
    original_path = history_store.get_path()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_history_file = pathlib.Path(temp_dir) / "history.json"
        history_store.set_path(str(temp_history_file))
        try:
            with TestClient(app) as client:
                clear_resp = client.delete("/history")
                assert clear_resp.status_code == 200

                _create_success_item(client)
                _create_success_item(client)
                _create_failure_item(client)

                default_resp = client.get("/export/markdown")
                assert default_resp.status_code == 200
                assert default_resp.headers.get("content-type", "").startswith("text/markdown")
                default_md = default_resp.text
                assert "# VoiceFlow Input Transcript Export" in default_md
                assert "- Exported Count: 3" in default_md
                assert "- Total History Count: 3" in default_md
                assert "- Success Only: false" in default_md
                assert "mock transcription" in default_md
                assert "- engine:" in default_md
                assert "- latency_ms:" in default_md

                limit_resp = client.get("/export/markdown?limit=1")
                assert limit_resp.status_code == 200
                limit_md = limit_resp.text
                assert "- Exported Count: 1" in limit_md
                assert limit_md.count("### ") == 1
                assert "NO_SPEECH_DETECTED" in limit_md

                success_only_resp = client.get("/export/markdown?success_only=true")
                assert success_only_resp.status_code == 200
                success_md = success_only_resp.text
                assert "- Success Only: true" in success_md
                assert "- Exported Count: 2" in success_md
                assert "NO_SPEECH_DETECTED" not in success_md

                clear_resp_2 = client.delete("/history")
                assert clear_resp_2.status_code == 200

                empty_resp = client.get("/export/markdown")
                assert empty_resp.status_code == 200
                empty_md = empty_resp.text
                assert "# VoiceFlow Input Transcript Export" in empty_md
                assert "## No Records" in empty_md
        finally:
            history_store.set_path(original_path)
    print("markdown_export_smoke: PASS")


if __name__ == "__main__":
    main()
