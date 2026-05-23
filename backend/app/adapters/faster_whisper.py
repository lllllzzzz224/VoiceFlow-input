from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import time
from typing import Any

from app.adapters.base import TranscriptionInput
from app.contracts import AsrEngine, Segment, TranscriptionData
from app.settings import settings


class FasterWhisperAdapter:
    engine = AsrEngine.FASTER_WHISPER
    _model: Any = None
    _model_key: tuple[str, str, str] | None = None
    _model_lock = threading.Lock()

    async def transcribe(self, payload: TranscriptionInput) -> TranscriptionData:
        return await asyncio.to_thread(self._transcribe_sync, payload)

    def _get_model(self) -> Any:
        model_key = (
            settings.faster_whisper_model,
            settings.faster_whisper_device,
            settings.faster_whisper_compute_type,
        )
        with self._model_lock:
            if self._model is not None and self._model_key == model_key:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except Exception as exc:
                raise RuntimeError(f"faster-whisper import failed: {exc}") from exc
            try:
                self._model = WhisperModel(
                    settings.faster_whisper_model,
                    device=settings.faster_whisper_device,
                    compute_type=settings.faster_whisper_compute_type,
                )
                self._model_key = model_key
            except Exception as exc:
                raise RuntimeError(f"faster-whisper model init failed: {exc}") from exc
            return self._model

    def _transcribe_sync(self, payload: TranscriptionInput) -> TranscriptionData:
        if len(payload.audio_bytes) == 0:
            return TranscriptionData(raw_text="", segments=[], engine=self.engine, latency_ms=1)

        model = self._get_model()
        started_at = time.perf_counter()
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
                tmp_file.write(payload.audio_bytes)
                tmp_path = tmp_file.name

            segments_iter, _ = model.transcribe(tmp_path, language=payload.language)
            segments: list[Segment] = []
            text_parts: list[str] = []
            for seg in segments_iter:
                seg_text = (seg.text or "").strip()
                segments.append(
                    Segment(
                        start_ms=int(max(seg.start, 0) * 1000),
                        end_ms=int(max(seg.end, 0) * 1000),
                        text=seg_text,
                    )
                )
                if seg_text:
                    text_parts.append(seg_text)

            raw_text = " ".join(text_parts).strip()
            latency_ms = max(int((time.perf_counter() - started_at) * 1000), 1)
            return TranscriptionData(
                raw_text=raw_text,
                segments=segments,
                engine=self.engine,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            raise RuntimeError(f"faster-whisper transcription failed: {exc}") from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
