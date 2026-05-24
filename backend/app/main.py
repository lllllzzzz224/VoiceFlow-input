from __future__ import annotations

import base64
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.adapters.base import TranscriptionInput
from app.adapters.deepseek_summary import DeepSeekMeetingSummaryProvider
from app.adapters.faster_whisper import AsrProcessingError
from app.adapters.xiaomi_mimo import MeetingSummaryProviderError, XiaomiMimoMeetingSummaryProvider
from app.asr_service import get_asr_adapter
from app.contracts import ErrorCode, ErrorInfo, StandardResult
from app.history import history_store
from app.postprocess import run_postprocess
from app.settings import settings
from app.transcript_state import TranscriptState

app = FastAPI(title="VoiceFlow Input Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
logger = logging.getLogger("voiceflow.backend")
xiaomi_meeting_summary_provider = XiaomiMimoMeetingSummaryProvider()
deepseek_meeting_summary_provider = DeepSeekMeetingSummaryProvider()


class MeetingSummaryRequest(BaseModel):
    transcript: str
    mode: str = "minutes"
    include_original: bool = True


def build_local_meeting_summary(transcript: str) -> str:
    trimmed = transcript.strip()
    clipped = trimmed if len(trimmed) <= 1200 else f"{trimmed[:1200]}\n...(truncated)"
    return (
        "# \u4f1a\u8bae\u7eaa\u8981\n\n"
        "## \u4f1a\u8bae\u6458\u8981\n"
        "- \u57fa\u4e8e\u5f53\u524d\u8f6c\u5199\u6587\u672c\u751f\u6210\u7684\u672c\u5730\u7eaa\u8981\u8349\u7a3f\u3002\n\n"
        "## \u5173\u952e\u7ed3\u8bba\n"
        "- \u672a\u63d0\u53ca\n\n"
        "## \u5f85\u529e\u4e8b\u9879\n"
        "- \u672a\u63d0\u53ca\n\n"
        "## \u98ce\u9669\u70b9\n"
        "- \u672a\u63d0\u53ca\n\n"
        "## \u539f\u59cb\u8981\u70b9\n"
        f"{clipped}\n"
    )


def _get_meeting_summary_provider() -> tuple[str, str, Any]:
    provider_name = settings.meeting_summary_provider
    if provider_name == "xiaomi":
        return provider_name, settings.xiaomi_model, xiaomi_meeting_summary_provider
    if provider_name == "deepseek":
        return provider_name, settings.deepseek_model, deepseek_meeting_summary_provider
    return "local", "local-template-v1", None


def _provider_key_available(provider_name: str) -> bool:
    if provider_name == "deepseek":
        return bool(settings.deepseek_api_key)
    if provider_name == "xiaomi":
        return bool(settings.xiaomi_api_key)
    return True


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ok_result(data: Any, meta: dict[str, Any] | None = None) -> StandardResult:
    return StandardResult(success=True, data=data, error=None, meta=meta or {})


def error_result(code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> StandardResult:
    return StandardResult(
        success=False,
        data=None,
        error=ErrorInfo(code=code, message=message, details=details or {}),
        meta={},
    )


def append_history_item(
    raw_text: str,
    final_text: str,
    engine: str,
    latency_ms: int,
    success: bool,
    error_code: str | None,
    audio_duration_ms: int = 0,
    decode_ms: int = 0,
    asr_ms: int = 0,
    postprocess_ms: int = 0,
    total_ms: int = 0,
) -> None:
    history_store.append(
        {
            "id": f"hist_{uuid4().hex[:12]}",
            "created_at": now_iso(),
            "raw_text": raw_text,
            "final_text": final_text,
            "engine": engine,
            "latency_ms": latency_ms,
            "success": success,
            "error_code": error_code,
            "audio_duration_ms": audio_duration_ms,
            "decode_ms": decode_ms,
            "asr_ms": asr_ms,
            "postprocess_ms": postprocess_ms,
            "total_ms": total_ms,
        }
    )


def asr_error_details(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, AsrProcessingError):
        details = {
            "engine": settings.asr_engine.value,
            "reason": exc.reason,
            "reason_detail": exc.message,
        }
        if exc.details:
            details.update(exc.details)
        return details
    return {
        "engine": settings.asr_engine.value,
        "reason": "unknown_error",
        "reason_detail": str(exc),
    }


def _merge_warning(postprocess_warning: str | None, audio_quality: dict[str, Any] | None) -> str | None:
    quality_warnings: list[str] = []
    if isinstance(audio_quality, dict):
        quality_warnings = list(audio_quality.get("warnings", []) or [])
    if not quality_warnings:
        return postprocess_warning
    quality_warning_text = f"AUDIO_QUALITY: {', '.join(quality_warnings)}"
    if postprocess_warning:
        return f"{postprocess_warning}; {quality_warning_text}"
    return quality_warning_text


def _parse_created_at(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def build_history_markdown(items: list[dict[str, Any]], total_count: int, success_only: bool) -> str:
    lines: list[str] = []
    lines.append("# VoiceFlow Input Transcript Export")
    lines.append("")
    lines.append(f"- Exported At: {now_iso()}")
    lines.append(f"- Exported Count: {len(items)}")
    lines.append(f"- Total History Count: {total_count}")
    lines.append(f"- Success Only: {str(success_only).lower()}")
    lines.append("")
    lines.append("> Large history export should use smaller `limit` values to avoid oversized payloads.")
    lines.append("")

    if not items:
        lines.append("## No Records")
        lines.append("")
        lines.append("No transcription history is available yet.")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Records")
    lines.append("")
    for idx, item in enumerate(items, start=1):
        created_at = str(item.get("created_at", ""))
        final_text = str(item.get("final_text", "")).strip()
        raw_text = str(item.get("raw_text", "")).strip()
        text_out = final_text if final_text else raw_text
        engine = str(item.get("engine", ""))
        latency_ms = item.get("latency_ms", "")
        audio_duration_ms = item.get("audio_duration_ms", "")
        decode_ms = item.get("decode_ms", "")
        asr_ms = item.get("asr_ms", "")
        postprocess_ms = item.get("postprocess_ms", "")
        total_ms = item.get("total_ms", "")
        success = item.get("success")
        error_code = item.get("error_code")

        lines.append(f"### {idx}. {created_at}")
        lines.append("")
        lines.append(f"- engine: {engine}")
        lines.append(f"- latency_ms: {latency_ms}")
        lines.append(f"- audio_duration_ms: {audio_duration_ms}")
        lines.append(f"- decode_ms: {decode_ms}")
        lines.append(f"- asr_ms: {asr_ms}")
        lines.append(f"- postprocess_ms: {postprocess_ms}")
        lines.append(f"- total_ms: {total_ms}")
        if success:
            lines.append("- success: true")
        else:
            lines.append(f"- error_code: {error_code}")
        lines.append("")
        lines.append(text_out if text_out else "(empty)")
        lines.append("")

    return "\n".join(lines)


@app.get("/health")
async def health() -> dict[str, Any]:
    result = ok_result(
        data={"status": "ok", "service": "voiceflow-input-backend"},
        meta={
            "asr_engine": settings.asr_engine.value,
            "asr_modes": {"fast": settings.asr_fast_model, "accurate": settings.asr_accurate_model},
            "version": "0.1.0",
            "time": now_iso(),
        },
    )
    return result.model_dump()


@app.get("/history")
async def get_history(
    limit: int = Query(default=50, ge=1, le=200),
    success_only: bool = Query(default=False),
) -> dict[str, Any]:
    all_items = history_store.list_items()
    sorted_items = sorted(all_items, key=lambda item: _parse_created_at(item.get("created_at")), reverse=True)
    if success_only:
        sorted_items = [item for item in sorted_items if item.get("success") is True]
    limited_items = sorted_items[:limit]
    result = ok_result(
        data={
            "items": limited_items,
            "count": len(limited_items),
            "total_count": len(all_items),
            "success_only": success_only,
            "limit": limit,
        },
        meta={"time": now_iso()},
    )
    return result.model_dump()


@app.delete("/history")
async def clear_history() -> dict[str, Any]:
    cleared = history_store.clear()
    result = ok_result(data={"cleared": cleared}, meta={"time": now_iso()})
    return result.model_dump()


@app.get("/export/markdown")
async def export_markdown(
    limit: int = Query(default=50, ge=1, le=200),
    success_only: bool = Query(default=False),
) -> Response:
    all_items = history_store.list_items()
    sorted_items = sorted(all_items, key=lambda item: _parse_created_at(item.get("created_at")), reverse=True)
    if success_only:
        sorted_items = [item for item in sorted_items if item.get("success") is True]
    limited_items = sorted_items[:limit]
    markdown = build_history_markdown(limited_items, total_count=len(all_items), success_only=success_only)
    return Response(content=markdown, media_type="text/markdown; charset=utf-8")


@app.post("/ai/meeting-summary")
async def meeting_summary(payload: MeetingSummaryRequest) -> dict[str, Any]:
    started = time.perf_counter()
    transcript = payload.transcript.strip()
    transcript_length = len(transcript)

    if not settings.ai_meeting_summary_enabled:
        result = error_result(ErrorCode.CONFIG_ERROR, "AI meeting summary is not configured.")
        result.meta = {"ai_enabled": False, "ai_used": False}
        return result.model_dump()

    if payload.mode != "minutes":
        result = error_result(ErrorCode.VALIDATION_ERROR, "Only mode=minutes is supported.")
        result.meta = {"ai_enabled": True, "ai_used": False}
        return result.model_dump()

    if not transcript:
        result = error_result(ErrorCode.VALIDATION_ERROR, "Transcript is empty.")
        result.meta = {"ai_enabled": True, "ai_used": False}
        return result.model_dump()

    provider_name, provider_model, provider = _get_meeting_summary_provider()

    if provider_name == "local":
        latency_ms = max(int((time.perf_counter() - started) * 1000), 1)
        result = ok_result(
            data={
                "summary_markdown": build_local_meeting_summary(transcript),
                "provider": "local_fallback",
                "model": "local-template-v1",
                "mode": payload.mode,
            },
            meta={
                "latency_ms": latency_ms,
                "ai_enabled": True,
                "ai_used": False,
                "provider_fallback": True,
                "fallback_reason": "provider_local_mode",
            },
        )
        return result.model_dump()

    if not _provider_key_available(provider_name):
        latency_ms = max(int((time.perf_counter() - started) * 1000), 1)
        result = ok_result(
            data={
                "summary_markdown": build_local_meeting_summary(transcript),
                "provider": "local_fallback",
                "model": "local-template-v1",
                "mode": payload.mode,
            },
            meta={
                "latency_ms": latency_ms,
                "ai_enabled": True,
                "ai_used": False,
                "provider_fallback": True,
                "fallback_reason": "provider_key_missing",
                "provider_error_code": "CONFIG_ERROR",
            },
        )
        return result.model_dump()

    try:
        summary_markdown = await provider.summarize(
            transcript=transcript,
            mode=payload.mode,
            include_original=payload.include_original,
        )
        latency_ms = max(int((time.perf_counter() - started) * 1000), 1)
        logger.info(
            "meeting_summary provider=%s model=%s success=%s latency_ms=%s transcript_length=%s",
            provider_name,
            provider_model,
            True,
            latency_ms,
            transcript_length,
        )
        result = ok_result(
            data={
                "summary_markdown": summary_markdown,
                "provider": provider_name,
                "model": provider_model,
                "mode": payload.mode,
            },
            meta={
                "latency_ms": latency_ms,
                "ai_enabled": True,
                "ai_used": True,
                "provider_fallback": False,
            },
        )
        return result.model_dump()
    except MeetingSummaryProviderError as exc:
        latency_ms = max(int((time.perf_counter() - started) * 1000), 1)
        logger.error(
            "meeting_summary provider=%s model=%s success=%s latency_ms=%s transcript_length=%s",
            provider_name,
            provider_model,
            False,
            latency_ms,
            transcript_length,
        )
        result = ok_result(
            data={
                "summary_markdown": build_local_meeting_summary(transcript),
                "provider": "local_fallback",
                "model": "local-template-v1",
                "mode": payload.mode,
            },
            meta={
                "latency_ms": latency_ms,
                "ai_enabled": True,
                "ai_used": True,
                "provider_fallback": True,
                "fallback_reason": "provider_request_failed",
                "provider_error_code": exc.reason,
            },
        )
        return result.model_dump()
    except Exception:
        latency_ms = max(int((time.perf_counter() - started) * 1000), 1)
        logger.error(
            "meeting_summary provider=%s model=%s success=%s latency_ms=%s transcript_length=%s",
            provider_name,
            provider_model,
            False,
            latency_ms,
            transcript_length,
        )
        result = ok_result(
            data={
                "summary_markdown": build_local_meeting_summary(transcript),
                "provider": "local_fallback",
                "model": "local-template-v1",
                "mode": payload.mode,
            },
            meta={
                "latency_ms": latency_ms,
                "ai_enabled": True,
                "ai_used": True,
                "provider_fallback": True,
                "fallback_reason": "provider_unknown_error",
                "provider_error_code": "request_failed",
            },
        )
        return result.model_dump()


@app.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()

    sample_rate = 16000
    channels = 1
    language: str = settings.default_language
    asr_mode = "fast"
    asr_mode_provided = False
    asr_mode_fallback = False
    hotwords: list[str] = []
    session_hotword_map = settings.build_hotword_map_for_session([])
    audio_buffer = bytearray()
    streaming_mode = "full"
    partial_state = TranscriptState()
    raw_state = TranscriptState()
    segment_count = 0
    segment_total_decode_ms = 0
    segment_total_asr_ms = 0
    segment_total_postprocess_ms = 0
    segment_total_ms = 0
    last_audio_quality: dict[str, Any] | None = None
    last_model_name: str | None = None
    last_model_cached: bool = False

    async def fail_audio_too_large() -> None:
        append_history_item(
            raw_text="",
            final_text="",
            engine=settings.asr_engine.value,
            latency_ms=0,
            success=False,
            error_code=ErrorCode.AUDIO_TOO_LARGE.value,
        )
        await websocket.send_json(
            {
                "type": "transcription_result",
                "result": error_result(
                    ErrorCode.AUDIO_TOO_LARGE,
                    "Audio payload exceeds configured size limit.",
                    details={
                        "max_audio_bytes": settings.max_audio_bytes,
                        "bytes_received": len(audio_buffer),
                    },
                ).model_dump(),
            }
        )
        await websocket.close()

    async def run_asr_once(input_bytes: bytes, total_started: float) -> tuple[StandardResult, str, str]:
        adapter = get_asr_adapter()
        try:
            adapter_output = await adapter.transcribe(
                TranscriptionInput(
                    audio_bytes=input_bytes,
                    sample_rate=sample_rate,
                    channels=channels,
                    language=language,
                    hotwords=settings.get_effective_hotwords(hotwords),
                    asr_mode=asr_mode,
                    asr_mode_provided=asr_mode_provided,
                )
            )
            transcription = adapter_output.transcription
        except AsrProcessingError as exc:
            details = asr_error_details(exc)
            if exc.reason == "audio_too_long":
                raise
            if exc.reason == "no_speech_detected":
                raise
            raise
        except Exception:
            raise

        result = ok_result(
            data=transcription.model_dump(),
            meta={
                "model": adapter_output.model,
                "cost_cents": 0,
                "bytes_received": len(input_bytes),
                "decode_ms": adapter_output.decode_ms,
                "asr_ms": adapter_output.asr_ms,
                "audio_duration_ms": adapter_output.audio_duration_ms,
                "model_cached": adapter_output.model_cached,
                "audio_quality": adapter_output.audio_quality,
                "asr_mode": adapter_output.asr_mode,
                "hotwords_enabled": settings.hotwords_enabled,
                "hotwords_count": settings.hotwords_count,
            },
        )
        postprocess_started = time.perf_counter()
        final_text, corrections, post_warning = run_postprocess(
            raw_text=transcription.raw_text,
            hotword_map=session_hotword_map,
            punctuation_enabled=settings.postprocess_punctuation_enabled,
            spacing_enabled=settings.postprocess_spacing_enabled,
            simplified_chinese_enabled=settings.postprocess_simplified_chinese_enabled,
        )
        postprocess_ms = max(int((time.perf_counter() - postprocess_started) * 1000), 0)
        total_ms = max(int((time.perf_counter() - total_started) * 1000), 1)
        warning = _merge_warning(post_warning, adapter_output.audio_quality)
        result.meta["postprocess_ms"] = postprocess_ms
        result.meta["total_ms"] = total_ms
        result.meta["time"] = now_iso()
        if asr_mode_fallback:
            result.meta["asr_mode_fallback"] = True
        if result.data is not None:
            result.data["final_text"] = final_text
            result.data["applied_corrections"] = [item.model_dump() for item in corrections]
            result.data["warning"] = warning
        return result, transcription.raw_text, final_text

    try:
        while True:
            try:
                message = await websocket.receive()
            except RuntimeError as exc:
                if "disconnect" in str(exc).lower():
                    return
                raise

            if message.get("bytes") is not None:
                audio_buffer.extend(message["bytes"])
                if len(audio_buffer) > settings.max_audio_bytes:
                    await fail_audio_too_large()
                    return
                continue

            text_payload = message.get("text")
            if text_payload is None:
                continue

            try:
                data = json.loads(text_payload)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "result": error_result(
                            ErrorCode.CONFIG_ERROR,
                            "Invalid JSON message.",
                        ).model_dump(),
                    }
                )
                continue

            msg_type = data.get("type")
            if msg_type == "start":
                sample_rate = int(data.get("sample_rate", sample_rate))
                channels = int(data.get("channels", channels))
                language = str(data.get("language") or settings.default_language)
                hotwords = list(data.get("hotwords", []))
                session_hotword_map = settings.build_hotword_map_for_session(hotwords)
                requested_asr_mode = data.get("asr_mode")
                asr_mode_fallback = False
                if requested_asr_mode is None:
                    asr_mode = "fast"
                    asr_mode_provided = False
                else:
                    normalized_mode = str(requested_asr_mode).strip().lower()
                    if normalized_mode in ("fast", "accurate"):
                        asr_mode = normalized_mode
                        asr_mode_provided = True
                    else:
                        asr_mode = "fast"
                        asr_mode_provided = True
                        asr_mode_fallback = True
                requested_mode = str(data.get("streaming_mode", "") or "").strip().lower()
                streaming_mode = "segment" if requested_mode == "segment" else "full"
                if streaming_mode == "segment" and not settings.experimental_segment_streaming_enabled:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "result": error_result(
                                ErrorCode.CONFIG_ERROR,
                                "Segment streaming is disabled.",
                            ).model_dump(),
                        }
                    )
                    await websocket.close()
                    return
                await websocket.send_json(
                    {
                        "type": "ack",
                        "result": ok_result(
                            data={
                                "event": "start_received",
                                "sample_rate": sample_rate,
                                "channels": channels,
                                "streaming_mode": streaming_mode,
                                "asr_mode": asr_mode,
                                "asr_mode_provided": asr_mode_provided,
                                "asr_mode_fallback": asr_mode_fallback,
                            },
                            meta={"time": now_iso()},
                        ).model_dump(),
                    }
                )
                continue

            if msg_type == "audio_chunk":
                if streaming_mode == "segment":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "result": error_result(
                                ErrorCode.CONFIG_ERROR,
                                "audio_chunk is not supported in segment mode. Use audio_segment.",
                            ).model_dump(),
                        }
                    )
                    continue
                chunk_base64 = data.get("chunk_base64", "")
                try:
                    chunk = base64.b64decode(chunk_base64, validate=True)
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "result": error_result(
                                ErrorCode.AUDIO_CAPTURE_ERROR,
                                "chunk_base64 is not valid base64.",
                            ).model_dump(),
                        }
                    )
                    continue
                audio_buffer.extend(chunk)
                if len(audio_buffer) > settings.max_audio_bytes:
                    await fail_audio_too_large()
                    return
                continue

            if msg_type == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "result": ok_result(data={"event": "pong"}, meta={"time": now_iso()}).model_dump(),
                    }
                )
                continue

            if msg_type == "audio_segment":
                if streaming_mode != "segment":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "result": error_result(
                                ErrorCode.CONFIG_ERROR,
                                "audio_segment requires streaming_mode=segment.",
                            ).model_dump(),
                        }
                    )
                    continue

                segment_index = int(data.get("segment_index", 0) or 0)
                chunk_base64 = data.get("chunk_base64", "")
                try:
                    segment_bytes = base64.b64decode(chunk_base64, validate=True)
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "partial_error",
                            "result": StandardResult(
                                success=False,
                                data={"segment_index": segment_index},
                                error=ErrorInfo(
                                    code=ErrorCode.AUDIO_CAPTURE_ERROR,
                                    message="segment chunk_base64 is not valid base64.",
                                    details={},
                                ),
                                meta={},
                            ).model_dump(),
                        }
                    )
                    continue

                segment_started = time.perf_counter()
                try:
                    partial_result, partial_raw_text, partial_final_text = await run_asr_once(segment_bytes, segment_started)
                    partial_meta = partial_result.meta or {}
                    quality = partial_meta.get("audio_quality") or {}
                    segment_duration_ms = int(partial_meta.get("audio_duration_ms", 0) or 0)
                    min_ms = settings.segment_streaming_min_segment_seconds * 1000
                    max_ms = settings.segment_streaming_max_segment_seconds * 1000
                    if segment_duration_ms > 0 and (segment_duration_ms < min_ms or segment_duration_ms > max_ms):
                        await websocket.send_json(
                            {
                                "type": "partial_error",
                                "result": StandardResult(
                                    success=False,
                                    data={"segment_index": segment_index},
                                    error=ErrorInfo(
                                        code=ErrorCode.CONFIG_ERROR,
                                        message="Segment duration is outside configured bounds.",
                                        details={
                                            "audio_duration_ms": segment_duration_ms,
                                            "min_segment_ms": min_ms,
                                            "max_segment_ms": max_ms,
                                        },
                                    ),
                                    meta={},
                                ).model_dump(),
                            }
                        )
                        continue

                    merged_text = partial_state.append_partial(partial_final_text)
                    raw_state.append_partial(partial_raw_text)
                    segment_count += 1
                    segment_total_decode_ms += int(partial_meta.get("decode_ms", 0) or 0)
                    segment_total_asr_ms += int(partial_meta.get("asr_ms", 0) or 0)
                    segment_total_postprocess_ms += int(partial_meta.get("postprocess_ms", 0) or 0)
                    segment_total_ms += int(partial_meta.get("total_ms", 0) or 0)
                    last_audio_quality = quality
                    last_model_name = str(partial_meta.get("model", "") or "")
                    last_model_cached = bool(partial_meta.get("model_cached", False))

                    await websocket.send_json(
                        {
                            "type": "partial_transcription_result",
                            "result": StandardResult(
                                success=True,
                                data={
                                    "segment_index": segment_index,
                                    "partial_text": partial_final_text,
                                    "merged_text": merged_text,
                                    "is_final": bool(data.get("is_final", False)),
                                    "engine": settings.asr_engine.value,
                                },
                                error=None,
                                meta={
                                    "decode_ms": partial_meta.get("decode_ms", 0),
                                    "asr_ms": partial_meta.get("asr_ms", 0),
                                    "postprocess_ms": partial_meta.get("postprocess_ms", 0),
                                    "total_ms": partial_meta.get("total_ms", 0),
                                    "audio_duration_ms": partial_meta.get("audio_duration_ms", 0),
                                    "model": partial_meta.get("model", ""),
                                    "asr_mode": partial_meta.get("asr_mode", asr_mode),
                                    "model_cached": partial_meta.get("model_cached", False),
                                    "hotwords_enabled": partial_meta.get("hotwords_enabled", settings.hotwords_enabled),
                                    "hotwords_count": partial_meta.get("hotwords_count", settings.hotwords_count),
                                    "audio_quality": quality,
                                    "time": now_iso(),
                                },
                            ).model_dump(),
                        }
                    )
                except AsrProcessingError:
                    await websocket.send_json(
                        {
                            "type": "partial_error",
                            "result": StandardResult(
                                success=False,
                                data={"segment_index": segment_index},
                                error=ErrorInfo(
                                    code=ErrorCode.ASR_ENGINE_ERROR,
                                    message="Partial segment processing failed.",
                                    details={},
                                ),
                                meta={},
                            ).model_dump(),
                        }
                    )
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "partial_error",
                            "result": StandardResult(
                                success=False,
                                data={"segment_index": segment_index},
                                error=ErrorInfo(
                                    code=ErrorCode.ASR_ENGINE_ERROR,
                                    message="Partial segment processing failed.",
                                    details={},
                                ),
                                meta={},
                            ).model_dump(),
                        }
                    )
                continue

            if msg_type == "end":
                total_started = time.perf_counter()
                if streaming_mode == "segment":
                    if segment_count == 0:
                        append_history_item(
                            raw_text="",
                            final_text="",
                            engine=settings.asr_engine.value,
                            latency_ms=0,
                            success=False,
                            error_code=ErrorCode.NO_SPEECH_DETECTED.value,
                            total_ms=max(int((time.perf_counter() - total_started) * 1000), 1),
                        )
                        await websocket.send_json(
                            {
                                "type": "transcription_result",
                                "result": error_result(
                                    ErrorCode.NO_SPEECH_DETECTED,
                                    "No audio received.",
                                ).model_dump(),
                            }
                        )
                        await websocket.close()
                        return

                    merged_raw = raw_state.get_merged_text()
                    final_text, corrections, post_warning = run_postprocess(
                        raw_text=merged_raw,
                        hotword_map=session_hotword_map,
                        punctuation_enabled=settings.postprocess_punctuation_enabled,
                        spacing_enabled=settings.postprocess_spacing_enabled,
                        simplified_chinese_enabled=settings.postprocess_simplified_chinese_enabled,
                    )
                    warning = _merge_warning(post_warning, last_audio_quality)
                    final_total_ms = max(int((time.perf_counter() - total_started) * 1000), 1)
                    result = ok_result(
                        data={
                            "raw_text": merged_raw,
                            "segments": [],
                            "engine": settings.asr_engine.value,
                            "latency_ms": max(segment_total_decode_ms + segment_total_asr_ms, 1),
                            "final_text": final_text,
                            "applied_corrections": [item.model_dump() for item in corrections],
                            "warning": warning,
                        },
                        meta={
                            "model": last_model_name or settings.faster_whisper_model,
                            "cost_cents": 0,
                            "bytes_received": 0,
                            "decode_ms": segment_total_decode_ms,
                            "asr_ms": segment_total_asr_ms,
                            "postprocess_ms": segment_total_postprocess_ms,
                            "total_ms": segment_total_ms + final_total_ms,
                            "audio_duration_ms": 0,
                            "asr_mode": asr_mode,
                            "model_cached": last_model_cached,
                            "hotwords_enabled": settings.hotwords_enabled,
                            "hotwords_count": settings.hotwords_count,
                            "audio_quality": last_audio_quality or {},
                            "time": now_iso(),
                        },
                    )
                    append_history_item(
                        raw_text=merged_raw,
                        final_text=final_text,
                        engine=settings.asr_engine.value,
                        latency_ms=max(segment_total_decode_ms + segment_total_asr_ms, 1),
                        success=True,
                        error_code=None,
                        audio_duration_ms=0,
                        decode_ms=segment_total_decode_ms,
                        asr_ms=segment_total_asr_ms,
                        postprocess_ms=segment_total_postprocess_ms,
                        total_ms=segment_total_ms + final_total_ms,
                    )
                    await websocket.send_json({"type": "transcription_result", "result": result.model_dump()})
                    await websocket.close()
                    return

                if len(audio_buffer) == 0:
                    append_history_item(
                        raw_text="",
                        final_text="",
                        engine=settings.asr_engine.value,
                        latency_ms=0,
                        success=False,
                        error_code=ErrorCode.NO_SPEECH_DETECTED.value,
                        total_ms=max(int((time.perf_counter() - total_started) * 1000), 1),
                    )
                    await websocket.send_json(
                        {
                            "type": "transcription_result",
                            "result": error_result(
                                ErrorCode.NO_SPEECH_DETECTED,
                                "No audio received.",
                            ).model_dump(),
                        }
                    )
                    await websocket.close()
                    return

                try:
                    result, raw_text, final_text = await run_asr_once(bytes(audio_buffer), total_started)
                except AsrProcessingError as exc:
                    details = asr_error_details(exc)
                    if exc.reason == "audio_too_long":
                        overflow_duration = int(details.get("audio_duration_ms", 0) or 0)
                        overflow_total_ms = max(int((time.perf_counter() - total_started) * 1000), 1)
                        append_history_item(
                            raw_text="",
                            final_text="",
                            engine=settings.asr_engine.value,
                            latency_ms=0,
                            success=False,
                            error_code=ErrorCode.CONFIG_ERROR.value,
                            audio_duration_ms=overflow_duration,
                            total_ms=overflow_total_ms,
                        )
                        await websocket.send_json(
                            {
                                "type": "transcription_result",
                                "result": error_result(
                                    ErrorCode.CONFIG_ERROR,
                                    "Audio duration exceeds configured limit.",
                                    details=details,
                                ).model_dump(),
                            }
                        )
                        await websocket.close()
                        return
                    if exc.reason == "no_speech_detected":
                        append_history_item(
                            raw_text="",
                            final_text="",
                            engine=settings.asr_engine.value,
                            latency_ms=0,
                            success=False,
                            error_code=ErrorCode.NO_SPEECH_DETECTED.value,
                            total_ms=max(int((time.perf_counter() - total_started) * 1000), 1),
                        )
                        await websocket.send_json(
                            {
                                "type": "transcription_result",
                                "result": error_result(
                                    ErrorCode.NO_SPEECH_DETECTED,
                                    "No speech detected.",
                                    details=details,
                                ).model_dump(),
                            }
                        )
                        await websocket.close()
                        return
                    logger.error(
                        "ASR processing failed: engine=%s reason=%s detail=%s",
                        details.get("engine"),
                        details.get("reason"),
                        details.get("reason_detail"),
                    )
                    append_history_item(
                        raw_text="",
                        final_text="",
                        engine=settings.asr_engine.value,
                        latency_ms=0,
                        success=False,
                        error_code=ErrorCode.ASR_ENGINE_ERROR.value,
                        total_ms=max(int((time.perf_counter() - total_started) * 1000), 1),
                    )
                    await websocket.send_json(
                        {
                            "type": "transcription_result",
                            "result": error_result(
                                ErrorCode.ASR_ENGINE_ERROR,
                                "ASR processing failed.",
                                details=details,
                            ).model_dump(),
                        }
                    )
                    await websocket.close()
                    return
                except NotImplementedError as exc:
                    append_history_item(
                        raw_text="",
                        final_text="",
                        engine=settings.asr_engine.value,
                        latency_ms=0,
                        success=False,
                        error_code=ErrorCode.ASR_ENGINE_ERROR.value,
                        total_ms=max(int((time.perf_counter() - total_started) * 1000), 1),
                    )
                    await websocket.send_json(
                        {
                            "type": "transcription_result",
                            "result": error_result(
                                ErrorCode.ASR_ENGINE_ERROR,
                                str(exc),
                                details={"engine": settings.asr_engine.value},
                            ).model_dump(),
                        }
                    )
                    await websocket.close()
                    return
                except Exception as exc:
                    details = asr_error_details(exc)
                    logger.error(
                        "ASR processing failed: engine=%s reason=%s detail=%s",
                        details.get("engine"),
                        details.get("reason"),
                        details.get("reason_detail"),
                    )
                    append_history_item(
                        raw_text="",
                        final_text="",
                        engine=settings.asr_engine.value,
                        latency_ms=0,
                        success=False,
                        error_code=ErrorCode.ASR_ENGINE_ERROR.value,
                        total_ms=max(int((time.perf_counter() - total_started) * 1000), 1),
                    )
                    await websocket.send_json(
                        {
                            "type": "transcription_result",
                            "result": error_result(
                                ErrorCode.ASR_ENGINE_ERROR,
                                "ASR processing failed.",
                                details=details,
                            ).model_dump(),
                        }
                    )
                    await websocket.close()
                    return

                result_meta = result.meta or {}
                append_history_item(
                    raw_text=raw_text,
                    final_text=final_text,
                    engine=settings.asr_engine.value,
                    latency_ms=int((result.data or {}).get("latency_ms", 0) or 0),
                    success=True,
                    error_code=None,
                    audio_duration_ms=int(result_meta.get("audio_duration_ms", 0) or 0),
                    decode_ms=int(result_meta.get("decode_ms", 0) or 0),
                    asr_ms=int(result_meta.get("asr_ms", 0) or 0),
                    postprocess_ms=int(result_meta.get("postprocess_ms", 0) or 0),
                    total_ms=int(result_meta.get("total_ms", 0) or 0),
                )
                await websocket.send_json({"type": "transcription_result", "result": result.model_dump()})
                await websocket.close()
                return

            await websocket.send_json(
                {
                    "type": "error",
                    "result": error_result(
                        ErrorCode.CONFIG_ERROR,
                        f"Unsupported message type: {msg_type}",
                    ).model_dump(),
                }
            )

    except WebSocketDisconnect:
        return
