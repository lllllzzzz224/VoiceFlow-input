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


class AsrAdapter(Protocol):
    engine: AsrEngine

    async def transcribe(self, payload: TranscriptionInput) -> TranscriptionData:
        ...


def make_single_segment(text: str) -> list[Segment]:
    return [Segment(start_ms=0, end_ms=0, text=text)]

