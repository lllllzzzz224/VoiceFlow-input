from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.contracts import AsrEngine, Segment, TranscriptionData


@dataclass
class TranscriptionInput:
    audio_bytes: bytes
    sample_rate: int = 16000
    channels: int = 1
    language: str | None = None
    hotwords: list[str] | None = None


@dataclass
class AdapterTranscriptionResult:
    transcription: TranscriptionData
    decode_ms: int
    asr_ms: int
    audio_duration_ms: int
    model_cached: bool
    model: str


class AsrAdapter(Protocol):
    engine: AsrEngine

    async def transcribe(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
        ...


def make_single_segment(text: str) -> list[Segment]:
    return [Segment(start_ms=0, end_ms=0, text=text)]

