from __future__ import annotations

import json
import os

from app.contracts import AsrEngine


class Settings:
    def __init__(self) -> None:
        raw_engine = os.getenv("ASR_ENGINE", AsrEngine.MOCK.value).strip().lower()
        self.asr_engine = AsrEngine(raw_engine) if raw_engine in AsrEngine._value2member_map_ else AsrEngine.MOCK
        self.mock_response_text = os.getenv("MOCK_RESPONSE_TEXT", "mock transcription").strip()

        self.faster_whisper_model = os.getenv("FASTER_WHISPER_MODEL", "base").strip() or "base"
        self.faster_whisper_device = os.getenv("FASTER_WHISPER_DEVICE", "cpu").strip() or "cpu"
        self.faster_whisper_compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"

        self.postprocess_punctuation_enabled = os.getenv("POSTPROCESS_PUNCTUATION_ENABLED", "true").strip().lower() != "false"
        self.postprocess_spacing_enabled = os.getenv("POSTPROCESS_SPACING_ENABLED", "true").strip().lower() != "false"
        self.history_file_path = os.getenv("HISTORY_FILE_PATH", "data/history.json").strip() or "data/history.json"
        self.hotword_map = self._load_hotword_map()

    def _load_hotword_map(self) -> dict[str, str]:
        default_map = {
            "qiniu": "\u4e03\u725b\u4e91",
            "qi niu yun": "\u4e03\u725b\u4e91",
            "kodo": "Kodo",
            "mcp": "MCP",
        }
        raw = os.getenv("HOTWORD_MAP_JSON", "").strip()
        if not raw:
            return default_map
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                return default_map
            normalized: dict[str, str] = {}
            for key, value in parsed.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                normalized[key] = value
            return normalized or default_map
        except Exception:
            return default_map


settings = Settings()

