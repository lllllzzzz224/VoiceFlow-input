from __future__ import annotations

import json
import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.adapters.xiaomi_mimo import MeetingSummaryProviderError
from app.main import app, meeting_summary_provider
from app.settings import settings


def assert_standard_result_shape(payload: dict) -> None:
    assert "success" in payload
    assert "data" in payload
    assert "error" in payload
    assert "meta" in payload


def main() -> None:
    original_enabled = settings.ai_meeting_summary_enabled
    original_key = settings.xiaomi_api_key
    original_model = settings.xiaomi_model
    original_summarize = meeting_summary_provider.summarize

    try:
        with TestClient(app) as client:
            settings.ai_meeting_summary_enabled = False
            settings.xiaomi_api_key = ""
            disabled_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "hello", "mode": "minutes", "include_original": True},
            )
            assert disabled_resp.status_code == 200
            disabled_payload = disabled_resp.json()
            assert_standard_result_shape(disabled_payload)
            assert disabled_payload["success"] is False
            assert disabled_payload["error"]["code"] == "CONFIG_ERROR"
            assert disabled_payload["meta"]["ai_enabled"] is False
            assert disabled_payload["meta"]["ai_used"] is False

            settings.ai_meeting_summary_enabled = True
            settings.xiaomi_api_key = ""
            missing_key_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "hello", "mode": "minutes", "include_original": True},
            )
            assert missing_key_resp.status_code == 200
            missing_key_payload = missing_key_resp.json()
            assert_standard_result_shape(missing_key_payload)
            assert missing_key_payload["success"] is False
            assert missing_key_payload["error"]["code"] == "CONFIG_ERROR"
            assert missing_key_payload["meta"]["ai_enabled"] is False
            assert missing_key_payload["meta"]["ai_used"] is False

            settings.ai_meeting_summary_enabled = True
            settings.xiaomi_api_key = "local-test-key"
            empty_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "   ", "mode": "minutes", "include_original": True},
            )
            assert empty_resp.status_code == 200
            empty_payload = empty_resp.json()
            assert_standard_result_shape(empty_payload)
            assert empty_payload["success"] is False
            assert empty_payload["error"]["code"] == "VALIDATION_ERROR"
            assert empty_payload["meta"]["ai_enabled"] is True
            assert empty_payload["meta"]["ai_used"] is False

            async def fake_success(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                return "# 会议纪要\n\n会议摘要\n- 示例"

            meeting_summary_provider.summarize = fake_success  # type: ignore[assignment]
            success_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "会议内容", "mode": "minutes", "include_original": True},
            )
            assert success_resp.status_code == 200
            success_payload = success_resp.json()
            assert_standard_result_shape(success_payload)
            assert success_payload["success"] is True
            assert success_payload["error"] is None
            assert success_payload["data"]["provider"] == "xiaomi_mimo"
            assert success_payload["data"]["model"] == settings.xiaomi_model
            assert success_payload["data"]["mode"] == "minutes"
            assert isinstance(success_payload["data"]["summary_markdown"], str)
            assert success_payload["meta"]["ai_enabled"] is True
            assert success_payload["meta"]["ai_used"] is True
            assert "latency_ms" in success_payload["meta"]

            async def fake_failure(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                raise MeetingSummaryProviderError("http_error", "Bearer token failure Authorization header")

            meeting_summary_provider.summarize = fake_failure  # type: ignore[assignment]
            provider_fail_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "会议内容", "mode": "minutes", "include_original": True},
            )
            assert provider_fail_resp.status_code == 200
            provider_fail_payload = provider_fail_resp.json()
            assert_standard_result_shape(provider_fail_payload)
            assert provider_fail_payload["success"] is False
            assert provider_fail_payload["error"]["code"] == "AI_PROVIDER_ERROR"
            assert provider_fail_payload["meta"]["ai_enabled"] is True
            assert provider_fail_payload["meta"]["ai_used"] is True
            assert "latency_ms" in provider_fail_payload["meta"]

            provider_fail_text = json.dumps(provider_fail_payload, ensure_ascii=False)
            forbidden_keywords = ["Bearer", "Authorization", "XIAOMI_API_KEY", "token"]
            for keyword in forbidden_keywords:
                assert keyword not in provider_fail_text
    finally:
        settings.ai_meeting_summary_enabled = original_enabled
        settings.xiaomi_api_key = original_key
        settings.xiaomi_model = original_model
        meeting_summary_provider.summarize = original_summarize  # type: ignore[assignment]

    print("meeting_summary_smoke: PASS")


if __name__ == "__main__":
    main()
