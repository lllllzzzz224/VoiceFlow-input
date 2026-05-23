from __future__ import annotations

from app.adapters.base import AdapterTranscriptionResult, TranscriptionInput
from app.contracts import AsrEngine


class XiaomiApiAdapter:
    engine = AsrEngine.XIAOMI_API

    async def transcribe(self, payload: TranscriptionInput) -> AdapterTranscriptionResult:
        raise NotImplementedError(
            "Xiaomi API adapter boundary placeholder. Keep credentials and API wiring outside committed code."
        )

