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
from app.audio_quality import analyze_audio_quality
from app.contracts import AsrEngine, Segment, TranscriptionData
from app.settings import settings

_WHISPER_SAMPLE_RATE = 16000


class AsrProcessingError(RuntimeError):
    def __init__(self, reason: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.details = details or {}


def _is_ffmpeg_runnable(binary_path: str) -> bool:
    try:
        proc = subprocess.run([binary_path, "-version"], capture_output=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


def _find_ffmpeg() -> str:
    env_binary = os.getenv("FFMPEG_BINARY", "").strip()
    if env_binary and os.path.isfile(env_binary) and _is_ffmpeg_runnable(env_binary):
        return os.path.abspath(env_binary)

    found = shutil.which("ffmpeg")
    if found and _is_ffmpeg_runnable(found):
        return found

    for candidate in [
        "ffmpeg.exe",
        "ffmpeg",
        os.path.join("bin", "ffmpeg.exe"),
        os.path.join("bin", "ffmpeg"),
    ]:
        if os.path.isfile(candidate) and _is_ffmpeg_runnable(candidate):
            return os.path.abspath(candidate)

    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.isfile(bundled) and _is_ffmpeg_runnable(bundled):
            return bundled
    except Exception:
        pass

    raise AsrProcessingError("ffmpeg_missing", "no runnable ffmpeg found in env/path/local/imageio fallback")


def _load_audio_via_ffmpeg(file_path: str) -> np.ndarray:
    ffmpeg_bin = _find_ffmpeg()
    cmd = [
        ffmpeg_bin,
        "-nostdin",
        "-threads",
        "0",
        "-i",
        file_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(_WHISPER_SAMPLE_RATE),
        "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
    except FileNotFoundError:
        raise AsrProcessingError("ffmpeg_missing", "ffmpeg binary not found when executing subprocess")
    except subprocess.TimeoutExpired:
        raise AsrProcessingError("decode_failed", "ffmpeg decode timed out after 30 seconds")

    if proc.returncode != 0:
        if proc.returncode in (3221225781, -1073741515):
            raise AsrProcessingError(
                "missing_dependency",
                "ffmpeg executable failed to start (missing runtime DLL dependency, rc=0xC0000135)",
            )
        stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()
        raise AsrProcessingError("decode_failed", f"ffmpeg decode failed (rc={proc.returncode}): {stderr_text[-500:]}")

    raw_bytes = proc.stdout
    if len(raw_bytes) == 0:
        raise AsrProcessingError("decode_failed", "ffmpeg produced empty output; audio may be silent or corrupt")

    return np.frombuffer(raw_bytes, np.int16).astype(np.float32) / 32768.0


class FasterWhisperAdapter:
    engine = AsrEngine.FASTER_WHISPER
    _model_cache: dict[tuple[str, str, str], Any] = {}
    _model_lock = threading.Lock()

    async def transcribe(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
        return await asyncio.to_thread(self._transcribe_sync, payload)

    def _normalize_asr_mode(self, asr_mode: str | None) -> str:
        return "accurate" if (asr_mode or "").strip().lower() == "accurate" else "fast"

    def _resolve_model_name(self, payload: TranscriptionInput) -> tuple[str, str]:
        resolved_mode = self._normalize_asr_mode(payload.asr_mode)
        if payload.asr_mode_provided:
            if resolved_mode == "accurate":
                return settings.asr_accurate_model, resolved_mode
            return settings.asr_fast_model, resolved_mode

        if settings.faster_whisper_model_explicitly_set:
            return settings.faster_whisper_model, resolved_mode
        return settings.asr_fast_model, resolved_mode

    def _get_model(self, payload: TranscriptionInput) -> tuple[Any, bool, str, str]:
        model_name, resolved_mode = self._resolve_model_name(payload)
        model_key = (
            model_name,
            settings.faster_whisper_device,
            settings.faster_whisper_compute_type,
        )
        with self._model_lock:
            cached_model = self._model_cache.get(model_key)
            if cached_model is not None:
                return cached_model, True, model_name, resolved_mode
            try:
                from faster_whisper import WhisperModel
            except Exception as exc:
                raise AsrProcessingError("missing_dependency", f"faster-whisper import failed: {exc}") from exc
            try:
                model = WhisperModel(
                    model_name,
                    device=settings.faster_whisper_device,
                    compute_type=settings.faster_whisper_compute_type,
                )
                self._model_cache[model_key] = model
            except Exception as exc:
                raise AsrProcessingError("model_load_failed", f"faster-whisper model init failed: {exc}") from exc
            return model, False, model_name, resolved_mode

    def _transcribe_sync(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
        if len(payload.audio_bytes) == 0:
            return AdapterTranscriptionResult(
                transcription=TranscriptionData(raw_text="", segments=[], engine=self.engine, latency_ms=1),
                decode_ms=0,
                asr_ms=1,
                audio_duration_ms=0,
                audio_quality={
                    "audio_duration_ms": 0,
                    "rms": 0.0,
                    "peak": 0.0,
                    "silence_ratio": 1.0,
                    "too_short": True,
                    "low_volume": True,
                    "mostly_silent": True,
                    "warnings": ["TOO_SHORT", "LOW_VOLUME", "MOSTLY_SILENT"],
                },
                model_cached=False,
                model=settings.asr_fast_model,
                asr_mode="fast",
            )

        model, model_cached, model_name, resolved_mode = self._get_model(payload)
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
                tmp_file.write(payload.audio_bytes)
                tmp_path = tmp_file.name

            decode_start = time.perf_counter()
            audio_array = _load_audio_via_ffmpeg(tmp_path)
            decode_ms = max(int((time.perf_counter() - decode_start) * 1000), 1)
            audio_quality = analyze_audio_quality(audio_array, sample_rate=_WHISPER_SAMPLE_RATE)
            audio_duration_ms = int((len(audio_array) / _WHISPER_SAMPLE_RATE) * 1000)
            max_duration_ms = int(settings.max_recording_seconds * 1000)
            if audio_duration_ms > max_duration_ms:
                raise AsrProcessingError(
                    "audio_too_long",
                    "Audio duration exceeds configured limit.",
                    details={
                        "audio_duration_ms": audio_duration_ms,
                        "max_recording_seconds": settings.max_recording_seconds,
                    },
                )

            asr_start = time.perf_counter()
            transcribe_kwargs: dict[str, Any] = {
                "language": payload.language or settings.default_language,
                "beam_size": settings.faster_whisper_beam_size,
                "vad_filter": settings.faster_whisper_vad_filter,
                "condition_on_previous_text": settings.faster_whisper_condition_on_previous_text,
                "temperature": settings.faster_whisper_temperature,
            }
            initial_prompt = settings.build_initial_prompt(payload.hotwords)
            if initial_prompt:
                transcribe_kwargs["initial_prompt"] = initial_prompt
            segments_iter, _ = model.transcribe(audio_array, **transcribe_kwargs)
            asr_ms = max(int((time.perf_counter() - asr_start) * 1000), 1)

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
            if not raw_text and (audio_quality["too_short"] or audio_quality["mostly_silent"]):
                raise AsrProcessingError(
                    "no_speech_detected",
                    "No speech detected from audio.",
                    details={"audio_quality": audio_quality},
                )
            transcription = TranscriptionData(
                raw_text=raw_text,
                segments=segments,
                engine=self.engine,
                latency_ms=decode_ms + asr_ms,
            )
            return AdapterTranscriptionResult(
                transcription=transcription,
                decode_ms=decode_ms,
                asr_ms=asr_ms,
                audio_duration_ms=audio_duration_ms,
                audio_quality=audio_quality,
                model_cached=model_cached,
                model=model_name,
                asr_mode=resolved_mode,
            )
        except AsrProcessingError:
            raise
        except Exception as exc:
            raise AsrProcessingError("decode_failed", f"faster-whisper transcription failed: {exc}") from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
