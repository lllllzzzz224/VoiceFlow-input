from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any

import numpy as np

from app.adapters.base import AdapterTranscriptionResult, TranscriptionInput
from app.contracts import AsrEngine, Segment, TranscriptionData
from app.settings import settings

# Target sample rate expected by Whisper models.
_WHISPER_SAMPLE_RATE = 16000


class AsrProcessingError(RuntimeError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


def _find_ffmpeg() -> str:
    """Locate the ffmpeg binary. Checks PATH first, then falls back to
    the backend working directory (useful for bundled desktop builds)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    # Check common local locations relative to the backend root.
    for candidate in ["ffmpeg.exe", "ffmpeg", os.path.join("bin", "ffmpeg.exe"), os.path.join("bin", "ffmpeg")]:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    raise AsrProcessingError("ffmpeg_missing", "ffmpeg not found in PATH or working directory")


def _load_audio_via_ffmpeg(file_path: str) -> np.ndarray:
    """Use the ffmpeg CLI to decode any audio file into a 16 kHz mono
    float32 numpy array."""
    ffmpeg_bin = _find_ffmpeg()
    cmd = [
        ffmpeg_bin,
        "-nostdin",
        "-threads", "0",
        "-i", file_path,
        "-f", "s16le",          # raw PCM signed 16-bit little-endian
        "-ac", "1",             # mono
        "-acodec", "pcm_s16le",
        "-ar", str(_WHISPER_SAMPLE_RATE),
        "-",                    # pipe to stdout
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise AsrProcessingError("ffmpeg_missing", "ffmpeg binary not found when executing subprocess")
    except subprocess.TimeoutExpired:
        raise AsrProcessingError("decode_failed", "ffmpeg decode timed out after 30 seconds")

    if proc.returncode != 0:
        stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AsrProcessingError("decode_failed", f"ffmpeg decode failed (rc={proc.returncode}): {stderr_text[-500:]}")

    raw_bytes = proc.stdout
    if len(raw_bytes) == 0:
        raise AsrProcessingError("decode_failed", "ffmpeg produced empty output — audio may be silent or corrupt")

    # Convert s16le bytes → float32 array normalised to [-1.0, 1.0].
    audio = np.frombuffer(raw_bytes, np.int16).astype(np.float32) / 32768.0
    return audio


class FasterWhisperAdapter:
    engine = AsrEngine.FASTER_WHISPER
    _model: Any = None
    _model_key: tuple[str, str, str] | None = None
    _model_lock = threading.Lock()

    async def transcribe(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
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
                raise AsrProcessingError("missing_dependency", f"faster-whisper import failed: {exc}") from exc
            try:
                self._model = WhisperModel(
                    settings.faster_whisper_model,
                    device=settings.faster_whisper_device,
                    compute_type=settings.faster_whisper_compute_type,
                )
                self._model_key = model_key
            except Exception as exc:
                raise AsrProcessingError("model_load_failed", f"faster-whisper model init failed: {exc}") from exc
            return self._model

    def _transcribe_sync(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
        if len(payload.audio_bytes) == 0:
            return AdapterTranscriptionResult(
                transcription=TranscriptionData(raw_text="", segments=[], engine=self.engine, latency_ms=1),
                decode_ms=0,
                asr_ms=0,
                model=settings.faster_whisper_model,
            )

        model = self._get_model()
        started_at = time.perf_counter()
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
                tmp_file.write(payload.audio_bytes)
                tmp_path = tmp_file.name

            # Decode via ffmpeg subprocess
            decode_start = time.perf_counter()
            audio_array = _load_audio_via_ffmpeg(tmp_path)
            decode_ms = max(int((time.perf_counter() - decode_start) * 1000), 0)

            # Feed the numpy array directly to faster-whisper.
            asr_start = time.perf_counter()
            segments_iter, _ = model.transcribe(audio_array, language=payload.language)
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
            asr_ms = max(int((time.perf_counter() - asr_start) * 1000), 0)
            
            latency_ms = max(int((time.perf_counter() - started_at) * 1000), 1)
            transcription = TranscriptionData(
                raw_text=raw_text,
                segments=segments,
                engine=self.engine,
                latency_ms=latency_ms,
            )
            return AdapterTranscriptionResult(
                transcription=transcription,
                decode_ms=decode_ms,
                asr_ms=asr_ms,
                model=settings.faster_whisper_model,
            )
        except AsrProcessingError:
            raise
        except Exception as exc:
            error_text = str(exc)
            raise AsrProcessingError("decode_failed", f"faster-whisper transcription failed: {error_text}") from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
