from __future__ import annotations

from app.adapters.base import TranscriptionInput
from app.contracts import AsrEngine, TranscriptionData


class XiaomiApiAdapter:
    engine = AsrEngine.XIAOMI_API

    async def transcribe(self, payload: TranscriptionInput) -> TranscriptionData:
        raise NotImplementedError(
            "Xiaomi API adapter boundary placeholder. Keep credentials and API wiring outside committed code."
        )

