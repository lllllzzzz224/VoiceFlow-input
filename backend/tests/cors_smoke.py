from __future__ import annotations

import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.main import app


def main() -> None:
    origin = "http://localhost:8080"
    with TestClient(app) as client:
        options_resp = client.options(
            "/history",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert options_resp.status_code in (200, 204)
        assert options_resp.headers.get("access-control-allow-origin") == origin

        get_resp = client.get("/history", headers={"Origin": origin})
        assert get_resp.status_code == 200
        assert get_resp.headers.get("access-control-allow-origin") == origin
    print("cors_smoke: PASS")


if __name__ == "__main__":
    main()

