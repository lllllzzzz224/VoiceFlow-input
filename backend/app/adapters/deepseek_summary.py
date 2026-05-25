from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

from app.adapters.xiaomi_mimo import MeetingSummaryProviderError
from app.settings import settings


def _build_system_prompt() -> str:
    return (
        "你是 VoiceFlow Input 的会议纪要结构化助手。"
        "请只根据用户提供的会议转写文本提取信息，不要编造。"
        "不要改写数字、日期、专有名词、代码命令、URL。"
        "输出必须是合法 JSON，不要使用 Markdown 代码块。"
        "字段必须包含：summary, action_items, decisions, risks, open_questions, insights, timeline。"
        "action_items 每项包含 task, owner, deadline。"
        "timeline 每项包含 order, event。"
        "如果信息不足，使用空数组或“未提及”。"
    )


def _build_user_prompt(transcript: str) -> str:
    return (
        "请把以下会议转写整理为结构化 JSON。字段必须包含：\n"
        "summary: string\n"
        "action_items: array，每项包含 task, owner, deadline\n"
        "decisions: array of string\n"
        "risks: array of string\n"
        "open_questions: array of string\n"
        "insights: array of string\n"
        "timeline: array，每项包含 order, event\n\n"
        "如果没有对应信息，数组返回 []，owner/deadline 写“未提及”。\n\n"
        "<transcript>\n"
        f"{transcript}\n"
        "</transcript>"
    )


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise MeetingSummaryProviderError("invalid_response", "provider response has no choices")
    message = choices[0].get("message", {})
    if not isinstance(message, dict):
        raise MeetingSummaryProviderError("invalid_response", "provider response message invalid")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise MeetingSummaryProviderError("invalid_response", "provider response content is empty")
    return content.strip()


def _parse_structured_json(content: str) -> dict[str, Any]:
    normalized = content.strip()
    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        normalized = normalized.replace("json", "", 1).strip()
    try:
        parsed = json.loads(normalized)
    except Exception as exc:
        raise MeetingSummaryProviderError("invalid_structured_json", f"provider json parse failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise MeetingSummaryProviderError("invalid_structured_json", "provider response json is not an object")
    return parsed


class DeepSeekMeetingSummaryProvider:
    provider = "deepseek"

    async def summarize_structured(self, transcript: str, mode: str, include_original: bool) -> dict[str, Any]:
        return await asyncio.to_thread(self._summarize_structured_sync, transcript, mode, include_original)

    def _summarize_structured_sync(self, transcript: str, mode: str, include_original: bool) -> dict[str, Any]:
        _ = mode
        _ = include_original
        url = settings.deepseek_api_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.deepseek_model,
            "messages": [
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": _build_user_prompt(transcript)},
            ],
            "temperature": 0.2,
            "stream": False,
            "max_tokens": 1200,
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=body,
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_bytes = response.read()
        except urllib.error.HTTPError as exc:
            raise MeetingSummaryProviderError("http_error", f"provider http error: status={exc.code}") from exc
        except urllib.error.URLError as exc:
            raise MeetingSummaryProviderError("network_error", f"provider network error: {exc.reason}") from exc
        except Exception as exc:
            raise MeetingSummaryProviderError("request_failed", f"provider request failed: {exc}") from exc

        try:
            response_json = json.loads(response_bytes.decode("utf-8"))
            content = _extract_message_content(response_json)
            return _parse_structured_json(content)
        except MeetingSummaryProviderError:
            raise
        except Exception as exc:
            raise MeetingSummaryProviderError("parse_failed", f"provider response parse failed: {exc}") from exc
