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
        self.faster_whisper_beam_size = self._parse_positive_int(os.getenv("FASTER_WHISPER_BEAM_SIZE", "5").strip(), 5)
        self.faster_whisper_vad_filter = self._parse_bool(os.getenv("FASTER_WHISPER_VAD_FILTER", "true").strip(), True)
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "zh").strip() or "zh"
        self.asr_initial_prompt = os.getenv("ASR_INITIAL_PROMPT", "").strip()
        self.ai_meeting_summary_enabled = self._parse_bool(
            os.getenv("AI_MEETING_SUMMARY_ENABLED", "false").strip(),
            False,
        )
        self.xiaomi_api_key = os.getenv("XIAOMI_API_KEY", "").strip()
        self.xiaomi_api_base_url = (
            os.getenv("XIAOMI_API_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1").strip()
            or "https://token-plan-cn.xiaomimimo.com/v1"
        )
        self.xiaomi_model = os.getenv("XIAOMI_MODEL", "MiMo-V2.5").strip() or "MiMo-V2.5"

        self.postprocess_punctuation_enabled = os.getenv("POSTPROCESS_PUNCTUATION_ENABLED", "true").strip().lower() != "false"
        self.postprocess_spacing_enabled = os.getenv("POSTPROCESS_SPACING_ENABLED", "true").strip().lower() != "false"
        self.postprocess_simplified_chinese_enabled = self._parse_bool(
            os.getenv("POSTPROCESS_SIMPLIFIED_CHINESE_ENABLED", "true").strip(),
            True,
        )
        self.history_file_path = os.getenv("HISTORY_FILE_PATH", "data/history.json").strip() or "data/history.json"
        self.max_audio_bytes = self._parse_max_audio_bytes(os.getenv("MAX_AUDIO_BYTES", "8388608").strip())
        self.max_recording_seconds = self._parse_max_recording_seconds(os.getenv("MAX_RECORDING_SECONDS", "30").strip())
        self.cors_origins = self._load_cors_origins()
        self.hotword_map = self._load_hotword_map()

    def _parse_max_audio_bytes(self, raw: str) -> int:
        try:
            value = int(raw)
            return value if value > 0 else 8388608
        except Exception:
            return 8388608

    def _parse_max_recording_seconds(self, raw: str) -> float:
        try:
            value = float(raw)
            return value if value > 0 else 30.0
        except Exception:
            return 30.0

    def _parse_positive_int(self, raw: str, fallback: int) -> int:
        try:
            value = int(raw)
            return value if value > 0 else fallback
        except Exception:
            return fallback

    def _parse_bool(self, raw: str, fallback: bool) -> bool:
        normalized = raw.strip().lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
        return fallback

    def _load_cors_origins(self) -> list[str]:
        default_origins = [
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        raw = os.getenv("CORS_ORIGINS", "").strip()
        if not raw:
            return default_origins
        values = [item.strip() for item in raw.split(",") if item.strip()]
        if not values:
            return default_origins
        merged: list[str] = []
        for origin in default_origins + values:
            if origin not in merged:
                merged.append(origin)
        return merged

    def _load_hotword_map(self) -> dict[str, str]:
        default_map = {
            "qiniu": "\u4e03\u725b\u4e91",
            "qi niu yun": "\u4e03\u725b\u4e91",
            "kodo": "Kodo",
            "mcp": "MCP",
            "\u4e03\u725b\u4e91": "\u4e03\u725b\u4e91",
            "github": "GitHub",
            "fastapi": "FastAPI",
            "faster whisper": "faster-whisper",
            "faster-whisper": "faster-whisper",
            "websocket": "WebSocket",
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

