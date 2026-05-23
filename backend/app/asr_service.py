from __future__ import annotations

from app.adapters.base import AsrAdapter
from app.adapters.faster_whisper import FasterWhisperAdapter
from app.adapters.mock import MockAsrAdapter
from app.adapters.xiaomi_api import XiaomiApiAdapter
from app.contracts import AsrEngine
from app.settings import settings


def get_asr_adapter() -> AsrAdapter:
    if settings.asr_engine == AsrEngine.FASTER_WHISPER:
        return FasterWhisperAdapter()
    if settings.asr_engine == AsrEngine.XIAOMI_API:
        return XiaomiApiAdapter()
    return MockAsrAdapter(default_text=settings.mock_response_text)

