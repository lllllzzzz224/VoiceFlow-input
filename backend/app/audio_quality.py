from __future__ import annotations

from typing import Any

import numpy as np

from app.settings import settings


def analyze_audio_quality(audio_array: np.ndarray, sample_rate: int = 16000) -> dict[str, Any]:
    if audio_array.size == 0:
        return {
            "audio_duration_ms": 0,
            "rms": 0.0,
            "peak": 0.0,
            "silence_ratio": 1.0,
            "too_short": True,
            "low_volume": True,
            "mostly_silent": True,
            "warnings": ["TOO_SHORT", "LOW_VOLUME", "MOSTLY_SILENT"],
        }

    float_audio = audio_array.astype(np.float32, copy=False)
    duration_ms = int((len(float_audio) / sample_rate) * 1000)
    rms = float(np.sqrt(np.mean(np.square(float_audio))))
    peak = float(np.max(np.abs(float_audio)))
    silence_threshold = max(settings.low_volume_rms_threshold * 0.5, 0.001)
    silence_ratio = float(np.mean(np.abs(float_audio) < silence_threshold))

    too_short = duration_ms < settings.min_audio_duration_ms
    low_volume = rms < settings.low_volume_rms_threshold
    mostly_silent = silence_ratio > settings.mostly_silent_ratio_threshold

    warnings: list[str] = []
    if too_short:
        warnings.append("TOO_SHORT")
    if low_volume:
        warnings.append("LOW_VOLUME")
    if mostly_silent:
        warnings.append("MOSTLY_SILENT")

    return {
        "audio_duration_ms": duration_ms,
        "rms": round(rms, 6),
        "peak": round(peak, 6),
        "silence_ratio": round(silence_ratio, 6),
        "too_short": too_short,
        "low_volume": low_volume,
        "mostly_silent": mostly_silent,
        "warnings": warnings,
    }
