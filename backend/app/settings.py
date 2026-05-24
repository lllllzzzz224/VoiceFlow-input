from __future__ import annotations

import json
import os

from app.contracts import AsrEngine


class Settings:
    def __init__(self) -> None:
        raw_engine = os.getenv("ASR_ENGINE", AsrEngine.MOCK.value).strip().lower()
        self.asr_engine = AsrEngine(raw_engine) if raw_engine in AsrEngine._value2member_map_ else AsrEngine.MOCK
        self.mock_response_text = os.getenv("MOCK_RESPONSE_TEXT", "mock transcription").strip()

        self.asr_quality_preset = self._parse_quality_preset(os.getenv("ASR_QUALITY_PRESET", "fast").strip())
        explicit_model = os.getenv("FASTER_WHISPER_MODEL", "").strip()
        self.faster_whisper_model_explicitly_set = bool(explicit_model)
        if explicit_model:
            self.faster_whisper_model = explicit_model
        else:
            self.faster_whisper_model = "small" if self.asr_quality_preset == "accurate" else "base"
        self.asr_fast_model = os.getenv("ASR_FAST_MODEL", "base").strip() or "base"
        self.asr_accurate_model = os.getenv("ASR_ACCURATE_MODEL", "small").strip() or "small"

        self.faster_whisper_device = os.getenv("FASTER_WHISPER_DEVICE", "cpu").strip() or "cpu"
        self.faster_whisper_compute_type = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"
        self.faster_whisper_beam_size = self._parse_positive_int(os.getenv("FASTER_WHISPER_BEAM_SIZE", "5").strip(), 5)
        self.faster_whisper_vad_filter = self._parse_bool(os.getenv("FASTER_WHISPER_VAD_FILTER", "true").strip(), True)
        self.faster_whisper_condition_on_previous_text = self._parse_bool(
            os.getenv("FASTER_WHISPER_CONDITION_ON_PREVIOUS_TEXT", "false").strip(),
            False,
        )
        self.faster_whisper_temperature = self._parse_non_negative_float(
            os.getenv("FASTER_WHISPER_TEMPERATURE", "0").strip(),
            0.0,
        )
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "zh").strip() or "zh"
        self.asr_initial_prompt = os.getenv("ASR_INITIAL_PROMPT", "").strip()
        self.asr_hotwords = self._load_asr_hotwords()

        self.postprocess_punctuation_enabled = self._parse_bool(
            os.getenv("POSTPROCESS_PUNCTUATION_ENABLED", "true").strip(),
            True,
        )
        self.postprocess_spacing_enabled = self._parse_bool(
            os.getenv("POSTPROCESS_SPACING_ENABLED", "true").strip(),
            True,
        )
        self.postprocess_simplified_chinese_enabled = self._parse_bool(
            os.getenv("POSTPROCESS_SIMPLIFIED_CHINESE_ENABLED", "true").strip(),
            True,
        )

        self.max_audio_bytes = self._parse_positive_int(os.getenv("MAX_AUDIO_BYTES", "8388608").strip(), 8388608)
        self.max_recording_seconds = self._parse_non_negative_float(os.getenv("MAX_RECORDING_SECONDS", "30").strip(), 30.0)
        self.min_audio_duration_ms = self._parse_positive_int(os.getenv("MIN_AUDIO_DURATION_MS", "1000").strip(), 1000)
        self.low_volume_rms_threshold = self._parse_non_negative_float(
            os.getenv("LOW_VOLUME_RMS_THRESHOLD", "0.008").strip(),
            0.008,
        )
        self.mostly_silent_ratio_threshold = self._parse_non_negative_float(
            os.getenv("MOSTLY_SILENT_RATIO_THRESHOLD", "0.85").strip(),
            0.85,
        )

        self.experimental_segment_streaming_enabled = self._parse_bool(
            os.getenv("EXPERIMENTAL_SEGMENT_STREAMING_ENABLED", "false").strip(),
            False,
        )
        self.segment_streaming_max_segment_seconds = self._parse_positive_int(
            os.getenv("SEGMENT_STREAMING_MAX_SEGMENT_SECONDS", "5").strip(),
            5,
        )
        self.segment_streaming_min_segment_seconds = self._parse_positive_int(
            os.getenv("SEGMENT_STREAMING_MIN_SEGMENT_SECONDS", "1").strip(),
            1,
        )

        self.ai_meeting_summary_enabled = self._parse_bool(
            os.getenv("AI_MEETING_SUMMARY_ENABLED", "false").strip(),
            False,
        )
        self.meeting_summary_provider = self._parse_meeting_summary_provider(
            os.getenv("MEETING_SUMMARY_PROVIDER", "deepseek").strip()
        )
        self.xiaomi_api_key = os.getenv("XIAOMI_API_KEY", "").strip()
        self.xiaomi_api_base_url = (
            os.getenv("XIAOMI_API_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1").strip()
            or "https://token-plan-cn.xiaomimimo.com/v1"
        )
        self.xiaomi_model = os.getenv("XIAOMI_MODEL", "MiMo-V2.5").strip() or "MiMo-V2.5"
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.deepseek_api_base_url = (
            os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com").strip()
            or "https://api.deepseek.com"
        )
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"

        self.history_file_path = os.getenv("HISTORY_FILE_PATH", "data/history.json").strip() or "data/history.json"
        self.cors_origins = self._load_cors_origins()
        self.hotword_map = self._build_base_hotword_map()

    @property
    def hotwords_enabled(self) -> bool:
        return len(self.asr_hotwords) > 0

    @property
    def hotwords_count(self) -> int:
        return len(self.asr_hotwords)

    def _parse_quality_preset(self, raw: str) -> str:
        normalized = raw.strip().lower()
        return normalized if normalized in ("fast", "accurate") else "fast"

    def _parse_meeting_summary_provider(self, raw: str) -> str:
        normalized = raw.strip().lower()
        return normalized if normalized in ("deepseek", "xiaomi", "local") else "deepseek"

    def _parse_positive_int(self, raw: str, fallback: int) -> int:
        try:
            value = int(raw)
            return value if value > 0 else fallback
        except Exception:
            return fallback

    def _parse_non_negative_float(self, raw: str, fallback: float) -> float:
        try:
            value = float(raw)
            return value if value >= 0 else fallback
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

    def _build_base_hotword_map(self) -> dict[str, str]:
        qiniu = "\u4e03\u725b\u4e91"
        default_map = {
            "qiniu": qiniu,
            "qi niu yun": qiniu,
            qiniu: qiniu,
            "kodo": "Kodo",
            "mcp": "MCP",
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

    def _load_asr_hotwords(self) -> list[str]:
        raw = os.getenv("ASR_HOTWORDS", "").strip()
        if not raw:
            return []
        words: list[str] = []
        for item in raw.split(","):
            word = item.strip()
            if not word:
                continue
            if word in words:
                continue
            words.append(word)
            if len(words) >= 30:
                break
        return words

    def get_effective_hotwords(self, runtime_hotwords: list[str] | None = None) -> list[str]:
        merged: list[str] = []
        for word in self.asr_hotwords:
            if word and word not in merged:
                merged.append(word)
        for word in runtime_hotwords or []:
            normalized = str(word).strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
        return merged[:30]

    def build_hotword_map_for_session(self, runtime_hotwords: list[str] | None = None) -> dict[str, str]:
        merged = dict(self.hotword_map)
        for word in self.get_effective_hotwords(runtime_hotwords):
            merged[word] = word
            merged[word.lower()] = word
        return merged

    def build_initial_prompt(self, runtime_hotwords: list[str] | None = None) -> str | None:
        if self.asr_initial_prompt:
            return self.asr_initial_prompt

        terms = self.get_effective_hotwords(runtime_hotwords)
        if not terms:
            return None

        joined_terms = ", ".join(terms[:30])
        prompt = (
            "以下是普通话和少量英文技术词的语音输入。"
            "请优先识别为简体中文。"
            f"可能出现的术语包括：{joined_terms}"
        )
        if len(prompt) > 300:
            trimmed_terms: list[str] = []
            for term in terms[:30]:
                candidate = ", ".join(trimmed_terms + [term])
                candidate_prompt = (
                    "以下是普通话和少量英文技术词的语音输入。"
                    "请优先识别为简体中文。"
                    f"可能出现的术语包括：{candidate}"
                )
                if len(candidate_prompt) > 300:
                    break
                trimmed_terms.append(term)
            if not trimmed_terms:
                return "以下是普通话语音输入。请优先识别为简体中文。"
            joined_terms = ", ".join(trimmed_terms)
            prompt = (
                "以下是普通话和少量英文技术词的语音输入。"
                "请优先识别为简体中文。"
                f"可能出现的术语包括：{joined_terms}"
            )
        return prompt


settings = Settings()
