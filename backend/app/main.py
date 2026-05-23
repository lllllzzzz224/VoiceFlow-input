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

from app.adapters.base import TranscriptionInput
from app.adapters.faster_whisper import AsrProcessingError
from app.asr_service import get_asr_adapter
from app.contracts import ErrorCode, ErrorInfo, StandardResult
from app.history import history_store
from app.postprocess import run_postprocess
from app.settings import settings

app = FastAPI(title="VoiceFlow Input Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
logger = logging.getLogger("voiceflow.backend")


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
        }
    )


def asr_error_details(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, AsrProcessingError):
        return {
            "engine": settings.asr_engine.value,
            "reason": exc.reason,
            "reason_detail": exc.message,
        }
    return {
        "engine": settings.asr_engine.value,
        "reason": "unknown_error",
        "reason_detail": str(exc),
    }


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
        success = item.get("success")
        error_code = item.get("error_code")

        lines.append(f"### {idx}. {created_at}")
        lines.append("")
        lines.append(f"- engine: {engine}")
        lines.append(f"- latency_ms: {latency_ms}")
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
        meta={"asr_engine": settings.asr_engine.value, "version": "0.1.0", "time": now_iso()},
    )
    return result.model_dump()


@app.get("/history")
async def get_history() -> dict[str, Any]:
    items = history_store.list_items()
    result = ok_result(data={"items": items, "count": len(items)}, meta={"time": now_iso()})
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


@app.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()

    sample_rate = 16000
    channels = 1
    language: str | None = None
    hotwords: list[str] = []
    audio_buffer = bytearray()

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
                language = data.get("language")
                hotwords = list(data.get("hotwords", []))
                await websocket.send_json(
                    {
                        "type": "ack",
                        "result": ok_result(
                            data={
                                "event": "start_received",
                                "sample_rate": sample_rate,
                                "channels": channels,
                            },
                            meta={"time": now_iso()},
                        ).model_dump(),
                    }
                )
                continue

            if msg_type == "audio_chunk":
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

            if msg_type == "end":
                total_started = time.perf_counter()
                if len(audio_buffer) == 0:
                    append_history_item(
                        raw_text="",
                        final_text="",
                        engine=settings.asr_engine.value,
                        latency_ms=0,
                        success=False,
                        error_code=ErrorCode.NO_SPEECH_DETECTED.value,
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

                adapter = get_asr_adapter()
                try:
                    adapter_output = await adapter.transcribe(
                        TranscriptionInput(
                            audio_bytes=bytes(audio_buffer),
                            sample_rate=sample_rate,
                            channels=channels,
                            language=language,
                            hotwords=hotwords,
                        )
                    )
                    transcription = adapter_output.transcription
                except NotImplementedError as exc:
                    append_history_item(
                        raw_text="",
                        final_text="",
                        engine=settings.asr_engine.value,
                        latency_ms=0,
                        success=False,
                        error_code=ErrorCode.ASR_ENGINE_ERROR.value,
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

                result = ok_result(
                    data=transcription.model_dump(),
                    meta={
                        "model": adapter_output.model,
                        "cost_cents": 0,
                        "bytes_received": len(audio_buffer),
                        "decode_ms": adapter_output.decode_ms,
                        "asr_ms": adapter_output.asr_ms,
                    },
                )
                postprocess_started = time.perf_counter()
                final_text, corrections, warning = run_postprocess(
                    raw_text=transcription.raw_text,
                    hotword_map=settings.hotword_map,
                    punctuation_enabled=settings.postprocess_punctuation_enabled,
                    spacing_enabled=settings.postprocess_spacing_enabled,
                )
                postprocess_ms = max(int((time.perf_counter() - postprocess_started) * 1000), 0)
                total_ms = max(int((time.perf_counter() - total_started) * 1000), 1)
                result.meta["postprocess_ms"] = postprocess_ms
                result.meta["total_ms"] = total_ms
                result.meta["time"] = now_iso()
                if result.data is not None:
                    result.data["final_text"] = final_text
                    result.data["applied_corrections"] = [item.model_dump() for item in corrections]
                    result.data["warning"] = warning
                append_history_item(
                    raw_text=transcription.raw_text,
                    final_text=final_text,
                    engine=transcription.engine.value,
                    latency_ms=transcription.latency_ms,
                    success=True,
                    error_code=None,
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
