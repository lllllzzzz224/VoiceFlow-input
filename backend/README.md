# VoiceFlow Input Backend (Web MVP)

Backend closed loop:

`browser recording -> WebSocket -> FastAPI -> ASR adapter -> postprocess -> history/export`

Default behavior is still **record-then-transcribe**.  
Experimental segment streaming is available but **disabled by default**.

## Quick Start (PowerShell)

```powershell
cd D:\qiniu\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Runtime Modes

`ASR_ENGINE=mock`:

- protocol联调与测试
- 不依赖模型

`ASR_ENGINE=faster_whisper`:

- 真实本地识别
- 需要可用 `ffmpeg`

## ASR Quality Preset

`ASR_QUALITY_PRESET=fast|accurate` (default `fast`)

- `fast`: default model `base`, lower latency
- `accurate`: default model `small`, better quality

Global model priority (when request does not pass `asr_mode`):

1. explicit `FASTER_WHISPER_MODEL` wins
2. otherwise use `ASR_QUALITY_PRESET`
3. fallback `base`

Request-level mode switching (`start.asr_mode`) for real runtime switching:

- `asr_mode=fast` -> `ASR_FAST_MODEL` (default `base`)
- `asr_mode=accurate` -> `ASR_ACCURATE_MODEL` (default `small`)
- missing `asr_mode` -> default `fast`
- invalid `asr_mode` -> fallback `fast` and mark `meta.asr_mode_fallback=true`

Models are lazy-loaded and cached by `(model, device, compute_type)`.
The first switch to a new model may be slower.

## Environment Variables

Core:

- `ASR_ENGINE=mock|faster_whisper`
- `ASR_QUALITY_PRESET=fast|accurate`
- `ASR_FAST_MODEL=base`
- `ASR_ACCURATE_MODEL=small`
- `DEFAULT_LANGUAGE=zh`
- `MAX_AUDIO_BYTES=8388608`
- `MAX_RECORDING_SECONDS=30`
- `ASR_HOTWORDS=` (optional comma-separated terms, for example `TermA,TermB,TermC`)

faster-whisper:

- `FASTER_WHISPER_MODEL=base|small`
- `FASTER_WHISPER_DEVICE=cpu`
- `FASTER_WHISPER_COMPUTE_TYPE=int8`
- `FASTER_WHISPER_BEAM_SIZE=5`
- `FASTER_WHISPER_VAD_FILTER=true`
- `FASTER_WHISPER_CONDITION_ON_PREVIOUS_TEXT=false`
- `FASTER_WHISPER_TEMPERATURE=0`
- `ASR_INITIAL_PROMPT=` (default empty, only passed when explicitly set)

Hotword enhancement behavior:

- when `ASR_HOTWORDS` is set, backend builds a short internal initial prompt
- prompt is length-limited (up to 30 terms / 300 chars)
- same hotwords are merged into postprocess hotword correction
- response exposes only `hotwords_enabled` and `hotwords_count` in `meta`

Postprocess:

- `POSTPROCESS_SIMPLIFIED_CHINESE_ENABLED=true`
- `POSTPROCESS_SPACING_ENABLED=true`
- `POSTPROCESS_PUNCTUATION_ENABLED=true`
- `HOTWORD_MAP_JSON` (optional)

Default hotword behavior includes:

- `七牛云`
- `Kodo`
- `MCP`
- `GitHub`
- `FastAPI`
- `faster-whisper`
- `WebSocket`

Audio quality warnings:

- `MIN_AUDIO_DURATION_MS=1000`
- `LOW_VOLUME_RMS_THRESHOLD=0.008`
- `MOSTLY_SILENT_RATIO_THRESHOLD=0.85`

Experimental segment streaming:

- `EXPERIMENTAL_SEGMENT_STREAMING_ENABLED=false`
- `SEGMENT_STREAMING_MIN_SEGMENT_SECONDS=1`
- `SEGMENT_STREAMING_MAX_SEGMENT_SECONDS=5`

History / CORS / optional AI summary:

- `HISTORY_FILE_PATH=data/history.json`
- `CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080`
- `AI_MEETING_SUMMARY_ENABLED=false`
- `MEETING_SUMMARY_PROVIDER=deepseek|xiaomi|local` (default `deepseek`)
- `DEEPSEEK_API_KEY=`
- `DEEPSEEK_API_BASE_URL=https://api.deepseek.com`
- `DEEPSEEK_MODEL=deepseek-v4-flash`
- `XIAOMI_API_KEY=`
- `XIAOMI_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1`
- `XIAOMI_MODEL=MiMo-V2.5`

Meeting summary provider notes:

- default demo provider is `deepseek`
- `xiaomi` is kept as optional provider only
- provider key is backend-only env var
- provider failure or missing key falls back to local markdown template
- fallback response uses `data.provider=local_fallback` and `meta.provider_fallback=true`
- Xiaomi Token Plan has backend automation limits, so it is not the recommended default demo provider

DeepSeek meeting-summary local run example:

```powershell
$env:AI_MEETING_SUMMARY_ENABLED="true"
$env:MEETING_SUMMARY_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="your_deepseek_api_key"
$env:DEEPSEEK_API_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
```

## API

### `GET /health`

Returns standard shape and active engine metadata.

### `WS /ws/transcribe`

Stable final envelope:

```json
{
  "type": "transcription_result",
  "result": {
    "success": true,
    "data": {},
    "error": null,
    "meta": {}
  }
}
```

Default record-then-transcribe messages:

1. `start` (supports optional `asr_mode=fast|accurate`)
2. binary audio chunk or `audio_chunk` base64 fallback
3. `end`

`meta` timing includes:

- `bytes_received`
- `decode_ms`
- `asr_ms`
- `postprocess_ms`
- `total_ms`
- `audio_duration_ms`
- `asr_mode`
- `model`
- `model_cached`
- `audio_quality`

Experimental segment mode:

- start with `"streaming_mode": "segment"`
- send `audio_segment` messages (each is a complete webm segment blob in base64)
- receive `partial_transcription_result` or `partial_error`
- `end` returns normal `transcription_result`

Notes:

- partial results are not written into history
- final result is written once
- no raw audio persistence
- no silero-vad; currently uses faster-whisper `vad_filter`

### `GET /history`

Query:

- `limit` (default `50`, min `1`, max `200`)
- `success_only` (default `false`)

### `DELETE /history`

Clear local transcript history.

### `GET /export/markdown`

Query:

- `limit` (default `50`, min `1`, max `200`)
- `success_only` (default `false`)

Returns `Content-Type: text/markdown; charset=utf-8`.

## CORS

For frontend `http://localhost:8080` -> backend `http://localhost:8000`, backend CORS is configured for local development origins by default.

Preflight check:

- `OPTIONS /history` should return success with `access-control-allow-origin`

## ffmpeg Notes

When using `ASR_ENGINE=faster_whisper`, backend decodes browser webm bytes through `ffmpeg`.

Lookup order:

1. `FFMPEG_BINARY`
2. system `PATH`
3. local `ffmpeg.exe` / `bin/ffmpeg.exe`
4. `imageio-ffmpeg` bundled binary

## Test Commands

```powershell
cd D:\qiniu\backend
python -m compileall app tests
python tests\postprocess_smoke.py
python tests\ws_mock_smoke.py
python tests\history_api_smoke.py
python tests\markdown_export_smoke.py
python tests\meeting_summary_smoke.py
python tests\segment_streaming_smoke.py
```
