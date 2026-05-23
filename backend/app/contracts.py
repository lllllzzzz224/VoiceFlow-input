from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MIC_PERMISSION_DENIED = "MIC_PERMISSION_DENIED"
    MIC_DEVICE_NOT_FOUND = "MIC_DEVICE_NOT_FOUND"
    NO_SPEECH_DETECTED = "NO_SPEECH_DETECTED"
    AUDIO_CAPTURE_ERROR = "AUDIO_CAPTURE_ERROR"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    ASR_ENGINE_ERROR = "ASR_ENGINE_ERROR"
    ASR_TIMEOUT = "ASR_TIMEOUT"
    POSTPROCESS_ERROR = "POSTPROCESS_ERROR"
    CLIPBOARD_ERROR = "CLIPBOARD_ERROR"
    PASTE_ERROR = "PASTE_ERROR"
    AI_PROVIDER_ERROR = "AI_PROVIDER_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class AsrEngine(str, Enum):
    FASTER_WHISPER = "faster_whisper"
    XIAOMI_API = "xiaomi_api"
    WHISPER_CPP = "whisper_cpp"
    VOSK = "vosk"
    SHERPA_ONNX = "sherpa_onnx"
    MOCK = "mock"


class ErrorInfo(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class StandardResult(BaseModel):
    success: bool
    data: Any | None
    error: ErrorInfo | None
    meta: dict[str, Any] = Field(default_factory=dict)


class Segment(BaseModel):
    start_ms: int
    end_ms: int
    text: str


class AppliedCorrection(BaseModel):
    from_text: str
    to_text: str
    correction_type: str


class TranscriptionData(BaseModel):
    raw_text: str
    segments: list[Segment]
    engine: AsrEngine
    latency_ms: int
    final_text: str | None = None
    applied_corrections: list[AppliedCorrection] = Field(default_factory=list)
    warning: str | None = None


class WsResultEnvelope(BaseModel):
    type: str
    result: StandardResult
