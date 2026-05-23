from __future__ import annotations

import time

from app.adapters.base import AdapterTranscriptionResult, TranscriptionInput, make_single_segment
from app.contracts import AsrEngine, TranscriptionData


class MockAsrAdapter:
    engine = AsrEngine.MOCK

    def __init__(self, default_text: str = "mock transcription") -> None:
        self._default_text = default_text

    async def transcribe(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
        started_at = time.perf_counter()
        byte_count = len(payload.audio_bytes)
        if byte_count == 0:
            text = ""
        else:
            text = f"{self._default_text} ({byte_count} bytes)"
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        transcription = TranscriptionData(
            raw_text=text,
            segments=make_single_segment(text),
            engine=self.engine,
            latency_ms=max(latency_ms, 1),
        )
        return AdapterTranscriptionResult(
            transcription=transcription,
            decode_ms=0,
            asr_ms=max(latency_ms, 1),
            audio_duration_ms=0,
            model_cached=True,
            model="mock-v1",
        )

