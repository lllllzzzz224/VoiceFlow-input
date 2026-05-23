from __future__ import annotations

from app.adapters.base import AsrAdapter
from app.adapters.faster_whisper import FasterWhisperAdapter
from app.adapters.mock import MockAsrAdapter
from app.adapters.xiaomi_api import XiaomiApiAdapter
from app.contracts import AsrEngine
from app.settings import settings

_ADAPTERS: dict[AsrEngine, AsrAdapter] = {}

def get_asr_adapter() -> AsrAdapter:
    engine = settings.asr_engine
    cached = _ADAPTERS.get(engine)
    if cached is not None:
        return cached

    if engine == AsrEngine.FASTER_WHISPER:
        adapter: AsrAdapter = FasterWhisperAdapter()
    elif engine == AsrEngine.XIAOMI_API:
        adapter = XiaomiApiAdapter()
    else:
        adapter = MockAsrAdapter(default_text=settings.mock_response_text)

    _ADAPTERS[engine] = adapter
    return adapter

