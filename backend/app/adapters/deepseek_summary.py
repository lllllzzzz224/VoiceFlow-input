from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from app.adapters.xiaomi_mimo import MeetingSummaryProviderError
from app.settings import settings


def _build_system_prompt() -> str:
    return (
        "\u4f60\u662f VoiceFlow Input \u7684\u4f1a\u8bae\u7eaa\u8981\u52a9\u624b\u3002"
        "\u8bf7\u6839\u636e\u7528\u6237\u63d0\u4f9b\u7684\u4f1a\u8bae\u8f6c\u5199\u6587\u672c\u751f\u6210\u7b80\u6d01\u3001\u7ed3\u6784\u5316\u7684 Markdown \u4f1a\u8bae\u7eaa\u8981\u3002"
        "\u4e0d\u8981\u7f16\u9020\u672a\u51fa\u73b0\u7684\u4fe1\u606f\uff1b"
        "\u4e0d\u8981\u6539\u5199\u6570\u5b57\u3001\u65e5\u671f\u3001\u4e13\u6709\u540d\u8bcd\u3001\u4ee3\u7801\u547d\u4ee4\u3001URL\uff1b"
        "\u5982\u679c\u4fe1\u606f\u4e0d\u8db3\uff0c\u8bf7\u5199\u201c\u672a\u63d0\u53ca\u201d\u3002"
    )


def _build_user_prompt(transcript: str) -> str:
    return (
        "\u8bf7\u5c06\u4ee5\u4e0b\u4f1a\u8bae\u8f6c\u5199\u6574\u7406\u4e3a Markdown \u4f1a\u8bae\u7eaa\u8981\uff0c"
        "\u5305\u542b\uff1a\u4f1a\u8bae\u6458\u8981\u3001\u5173\u952e\u7ed3\u8bba\u3001\u5f85\u529e\u4e8b\u9879\u3001\u98ce\u9669\u70b9\u3001\u539f\u59cb\u8981\u70b9\u3002\n\n"
        "<transcript>\n"
        f"{transcript}\n"
        "</transcript>"
    )


class DeepSeekMeetingSummaryProvider:
    provider = "deepseek"

    async def summarize(self, transcript: str, mode: str, include_original: bool) -> str:
        return await asyncio.to_thread(self._summarize_sync, transcript, mode, include_original)

    def _summarize_sync(self, transcript: str, mode: str, include_original: bool) -> str:
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
            choices = response_json.get("choices", [])
            if not choices:
                raise MeetingSummaryProviderError("invalid_response", "provider response has no choices")
            message = choices[0].get("message", {})
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise MeetingSummaryProviderError("invalid_response", "provider response content is empty")
            return content.strip()
        except MeetingSummaryProviderError:
            raise
        except Exception as exc:
            raise MeetingSummaryProviderError("parse_failed", f"provider response parse failed: {exc}") from exc
