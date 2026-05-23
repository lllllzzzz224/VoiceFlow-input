from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.adapters.base import TranscriptionInput
from app.asr_service import get_asr_adapter
from app.contracts import ErrorCode, ErrorInfo, StandardResult
from app.history import history_store
from app.postprocess import run_postprocess
from app.settings import settings

app = FastAPI(title="VoiceFlow Input Backend", version="0.1.0")


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


@app.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()

    sample_rate = 16000
    channels = 1
    language: str | None = None
    hotwords: list[str] = []
    audio_buffer = bytearray()

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
                    transcription = await adapter.transcribe(
                        TranscriptionInput(
                            audio_bytes=bytes(audio_buffer),
                            sample_rate=sample_rate,
                            channels=channels,
                            language=language,
                            hotwords=hotwords,
                        )
                    )
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
                                details={"engine": settings.asr_engine.value, "reason": str(exc)},
                            ).model_dump(),
                        }
                    )
                    await websocket.close()
                    return

                result = ok_result(
                    data=transcription.model_dump(),
                    meta={
                        "model": (
                            "mock-v1"
                            if transcription.engine.value == "mock"
                            else settings.faster_whisper_model
                            if transcription.engine.value == "faster_whisper"
                            else "pending"
                        ),
                        "cost_cents": 0,
                        "bytes_received": len(audio_buffer),
                        "time": now_iso(),
                    },
                )
                final_text, corrections, warning = run_postprocess(
                    raw_text=transcription.raw_text,
                    hotword_map=settings.hotword_map,
                    punctuation_enabled=settings.postprocess_punctuation_enabled,
                    spacing_enabled=settings.postprocess_spacing_enabled,
                )
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
