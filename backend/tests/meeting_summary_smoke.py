from __future__ import annotations

import json
import pathlib
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.adapters.xiaomi_mimo import MeetingSummaryProviderError
from app.main import app, deepseek_meeting_summary_provider
from app.settings import settings


def assert_standard_result_shape(payload: dict) -> None:
    assert "success" in payload
    assert "data" in payload
    assert "error" in payload
    assert "meta" in payload


def main() -> None:
    original_enabled = settings.ai_meeting_summary_enabled
    original_provider = settings.meeting_summary_provider
    original_deepseek_key = settings.deepseek_api_key
    original_deepseek_model = settings.deepseek_model
    original_summarize_structured = deepseek_meeting_summary_provider.summarize_structured

    try:
        with TestClient(app) as client:
            settings.ai_meeting_summary_enabled = False
            settings.meeting_summary_provider = "deepseek"
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
            settings.meeting_summary_provider = "deepseek"
            settings.deepseek_api_key = ""
            missing_key_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "hello", "mode": "minutes", "include_original": True},
            )
            assert missing_key_resp.status_code == 200
            missing_key_payload = missing_key_resp.json()
            assert_standard_result_shape(missing_key_payload)
            assert missing_key_payload["success"] is True
            assert missing_key_payload["data"]["provider"] == "local_fallback"
            assert isinstance(missing_key_payload["data"]["structured"], dict)
            assert missing_key_payload["meta"]["provider_fallback"] is True
            assert missing_key_payload["meta"]["provider_error_code"] == "CONFIG_ERROR"

            settings.deepseek_api_key = "local-test-key"
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
                return {
                    "summary": "这是摘要",
                    "action_items": [{"task": "整理发布", "owner": "未提及", "deadline": "未提及"}],
                    "decisions": ["继续推进"],
                    "risks": ["准确度风险"],
                    "open_questions": ["是否需要额外校验"],
                    "insights": ["准流式准确度是当前演示风险"],
                    "timeline": [{"order": 1, "event": "确认方案"}],
                }

            deepseek_meeting_summary_provider.summarize_structured = fake_success  # type: ignore[assignment]
            success_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "meeting content", "mode": "minutes", "include_original": True},
            )
            assert success_resp.status_code == 200
            success_payload = success_resp.json()
            assert_standard_result_shape(success_payload)
            assert success_payload["success"] is True
            assert success_payload["error"] is None
            assert success_payload["data"]["provider"] == "deepseek"
            assert success_payload["data"]["model"] == settings.deepseek_model
            assert success_payload["data"]["mode"] == "minutes"
            assert isinstance(success_payload["data"]["summary_markdown"], str)
            assert isinstance(success_payload["data"]["structured"], dict)
            assert "summary" in success_payload["data"]["structured"]
            assert "action_items" in success_payload["data"]["structured"]
            markdown = success_payload["data"]["summary_markdown"]
            assert "## 待办事项" in markdown
            assert "## 决策" in markdown
            assert "## 风险" in markdown
            assert success_payload["meta"]["ai_enabled"] is True
            assert success_payload["meta"]["ai_used"] is True
            assert success_payload["meta"]["provider_fallback"] is False
            assert "latency_ms" in success_payload["meta"]

            async def fake_invalid_json(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                raise MeetingSummaryProviderError("invalid_structured_json", "provider json parse failed")

            deepseek_meeting_summary_provider.summarize_structured = fake_invalid_json  # type: ignore[assignment]
            invalid_json_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "meeting content", "mode": "minutes", "include_original": True},
            )
            assert invalid_json_resp.status_code == 200
            invalid_json_payload = invalid_json_resp.json()
            assert_standard_result_shape(invalid_json_payload)
            assert invalid_json_payload["success"] is True
            assert invalid_json_payload["error"] is None
            assert invalid_json_payload["data"]["provider"] == "local_fallback"
            assert isinstance(invalid_json_payload["data"]["structured"], dict)
            assert invalid_json_payload["meta"]["provider_fallback"] is True
            assert invalid_json_payload["meta"]["fallback_reason"] == "invalid_structured_json"
            assert invalid_json_payload["meta"]["provider_error_code"] == "invalid_structured_json"

            async def fake_failure(*_args, **_kwargs):  # type: ignore[no-untyped-def]
                raise MeetingSummaryProviderError("http_error", "Bearer token failure Authorization header")

            deepseek_meeting_summary_provider.summarize_structured = fake_failure  # type: ignore[assignment]
            provider_fail_resp = client.post(
                "/ai/meeting-summary",
                json={"transcript": "meeting content", "mode": "minutes", "include_original": True},
            )
            assert provider_fail_resp.status_code == 200
            provider_fail_payload = provider_fail_resp.json()
            assert_standard_result_shape(provider_fail_payload)
            assert provider_fail_payload["success"] is True
            assert provider_fail_payload["error"] is None
            assert provider_fail_payload["data"]["provider"] == "local_fallback"
            assert isinstance(provider_fail_payload["data"]["structured"], dict)
            assert provider_fail_payload["meta"]["provider_fallback"] is True
            assert provider_fail_payload["meta"]["provider_error_code"] == "http_error"

            payload_text = json.dumps(provider_fail_payload, ensure_ascii=False)
            forbidden_keywords = ["Bearer", "Authorization", "XIAOMI_API_KEY", "DEEPSEEK_API_KEY", "token"]
            for keyword in forbidden_keywords:
                assert keyword not in payload_text
    finally:
        settings.ai_meeting_summary_enabled = original_enabled
        settings.meeting_summary_provider = original_provider
        settings.deepseek_api_key = original_deepseek_key
        settings.deepseek_model = original_deepseek_model
        deepseek_meeting_summary_provider.summarize_structured = original_summarize_structured  # type: ignore[assignment]

    print("meeting_summary_smoke: PASS")


if __name__ == "__main__":
    main()
