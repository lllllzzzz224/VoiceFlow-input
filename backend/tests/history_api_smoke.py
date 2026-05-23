from __future__ import annotations

import pathlib
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.history import history_store
from app.main import app


def assert_history_item_shape(item: dict) -> None:
    for key in ["id", "created_at", "raw_text", "final_text", "engine", "latency_ms", "success", "error_code"]:
        assert key in item


def main() -> None:
    original_path = history_store.get_path()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_history_file = pathlib.Path(temp_dir) / "history.json"
        history_store.set_path(str(temp_history_file))
        try:
            with TestClient(app) as client:
                clear_resp = client.delete("/history")
                assert clear_resp.status_code == 200

                with client.websocket_connect("/ws/transcribe") as ws:
                    ws.send_json({"type": "start", "sample_rate": 16000, "channels": 1})
                    _ = ws.receive_json()
                    ws.send_bytes(b"voice")
                    ws.send_json({"type": "end"})
                    msg = ws.receive_json()
                    assert msg["result"]["success"] is True

                with client.websocket_connect("/ws/transcribe") as ws:
                    ws.send_json({"type": "start"})
                    _ = ws.receive_json()
                    ws.send_json({"type": "end"})
                    msg = ws.receive_json()
                    assert msg["result"]["success"] is False
                    assert msg["result"]["error"]["code"] == "NO_SPEECH_DETECTED"

                history_resp = client.get("/history")
                assert history_resp.status_code == 200
                payload = history_resp.json()
                assert payload["success"] is True
                items = payload["data"]["items"]
                assert payload["data"]["count"] == 2
                assert len(items) == 2
                for item in items:
                    assert_history_item_shape(item)

                delete_resp = client.delete("/history")
                assert delete_resp.status_code == 200
                assert delete_resp.json()["data"]["cleared"] == 2

                history_resp_after = client.get("/history")
                assert history_resp_after.status_code == 200
                assert history_resp_after.json()["data"]["count"] == 0
                assert history_resp_after.json()["data"]["items"] == []
        finally:
            history_store.set_path(original_path)
    print("history_api_smoke: PASS")


if __name__ == "__main__":
    main()

