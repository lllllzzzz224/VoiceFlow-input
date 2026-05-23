# VoiceFlow Input Backend (Web MVP)

Minimal backend loop for Web MVP:

`browser audio recording -> WebSocket -> FastAPI -> ASR adapter -> transcription text`

Current recognition mode is **record-then-transcribe** (near-real-time after recording ends), not token/word-by-word streaming ASR.

Current implementation:

- `GET /health`
- `WS /ws/transcribe`
- audio chunk ingest via binary frame or JSON `chunk_base64`
- mock transcription result with stable response shape
- `faster-whisper` adapter integration and `xiaomi_api` boundary placeholder

## Quick Start (Windows PowerShell)

```powershell
cd D:\qiniu\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test

Run WebSocket mock smoke test:

```powershell
cd D:\qiniu\backend
python tests\ws_mock_smoke.py
python tests\postprocess_smoke.py
python tests\history_api_smoke.py
python tests\markdown_export_smoke.py
python tests\cors_smoke.py
```

This smoke test covers:

- `/health`
- WS connect
- `start`
- binary chunk
- `end`
- mock transcript result
- no-speech and base64 error path
- invalid JSON path
- unsupported message type path
- adapter failure path (`ASR_ENGINE_ERROR`)
- postprocess fixed sentence and failure fallback
- history write/read/clear API path
- markdown export API path (limit/success-only/empty history)
- CORS preflight and origin header path (`/history`)

Optional real faster-whisper smoke test:

```powershell
cd D:\qiniu\backend
$env:RUN_FASTER_WHISPER_TEST="1"
python tests\faster_whisper_optin_smoke.py
```

Reset to mock:

```powershell
$env:ASR_ENGINE="mock"
```

Run live checks against a running server:

```powershell
cd D:\qiniu\backend
python tests\ws_live_mock_checks.py --base-url http://127.0.0.1:8000
```

Run simple concurrency smoke (2-5 sessions):

```powershell
cd D:\qiniu\backend
python tests\ws_live_concurrency_smoke.py --base-url http://127.0.0.1:8000 --sessions 3
```

## API

### Health

```http
GET /health
```

Response shape:

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "voiceflow-input-backend"
  },
  "error": null,
  "meta": {
    "asr_engine": "mock",
    "version": "0.1.0",
    "time": "2026-05-23T00:00:00+00:00"
  }
}
```

### WebSocket Transcribe

```text
WS /ws/transcribe
```

Client message types:

1. `start` (JSON text frame)
2. audio chunk:
   - binary frame (`bytes`)
   - or JSON `{ "type": "audio_chunk", "chunk_base64": "..." }`
3. `end` (JSON text frame)

Example flow:

```json
{ "type": "start", "sample_rate": 16000, "channels": 1, "language": "zh", "hotwords": ["Kodo"] }
```

then send binary audio chunks, then:

```json
{ "type": "end" }
```

Server final message shape:

```json
{
  "type": "transcription_result",
  "result": {
    "success": true,
    "data": {
      "raw_text": "mock transcription (12345 bytes)",
      "segments": [
        { "start_ms": 0, "end_ms": 0, "text": "mock transcription (12345 bytes)" }
      ],
      "engine": "mock",
      "latency_ms": 1
    },
    "error": null,
    "meta": {
      "model": "mock-v1",
      "cost_cents": 0,
      "bytes_received": 12345,
      "decode_ms": 0,
      "asr_ms": 1,
      "postprocess_ms": 0,
      "total_ms": 2,
      "audio_duration_ms": 1250,
      "model_cached": true,
      "time": "2026-05-23T00:00:00+00:00"
    }
  }
}
```

`meta` timing fields:

- `bytes_received`: total audio payload size for the session
- `decode_ms`: decode stage latency (ffmpeg/media decode)
- `asr_ms`: model inference stage latency
- `postprocess_ms`: text postprocessing latency
- `total_ms`: total latency from `end` handling to final response
- `audio_duration_ms`: decoded audio duration after ffmpeg resample
- `model_cached`: whether current recognition reused cached model instance

### History API

```http
GET /history?limit=50&success_only=false
DELETE /history
```

`GET /history` response `data`:

```json
{
  "items": [
    {
      "id": "hist_xxx",
      "created_at": "2026-05-23T00:00:00+00:00",
      "raw_text": "string",
      "final_text": "string",
      "engine": "mock",
      "latency_ms": 1,
      "success": true,
      "error_code": null,
      "audio_duration_ms": 1250,
      "decode_ms": 120,
      "asr_ms": 610,
      "postprocess_ms": 3,
      "total_ms": 745
    }
  ],
  "count": 1,
  "total_count": 1,
  "success_only": false,
  "limit": 50
}
```

History is stored in local JSON and does not include raw audio.
Failure records only keep `error_code` and base metadata (engine/timing), with empty transcript text.

### Markdown Export API

```http
GET /export/markdown
```

Query params:

- `limit` (default `50`, min `1`, max `200`)
- `success_only` (default `false`)

Response:

- Content-Type: `text/markdown; charset=utf-8`
- Body: markdown text generated from local history
- Records are sorted by `created_at` descending and truncated by `limit`
- Per record includes:
  - `created_at`
  - `final_text` (fallback `raw_text` when final is empty)
  - `engine`
  - `latency_ms`
  - `success` / `error_code`
- Empty history still returns valid markdown with a "No Records" section.
- For very large history, keep `limit` small to avoid oversized exports.

## Config

Environment variables:

- `ASR_ENGINE` (`mock` by default)
- `MOCK_RESPONSE_TEXT` (`mock transcription` by default)
- `POSTPROCESS_PUNCTUATION_ENABLED` (`true` by default)
- `POSTPROCESS_SPACING_ENABLED` (`true` by default)
- `HOTWORD_MAP_JSON` (JSON object string, optional; defaults include `七牛云`, `Kodo`, `MCP`, `GitHub`, `FastAPI`, `faster-whisper`, `WebSocket`)
- `HISTORY_FILE_PATH` (`data/history.json` by default)
- `CORS_ORIGINS` (comma-separated, default includes `http://localhost:8080,http://127.0.0.1:8080`)
- `MAX_AUDIO_BYTES` (default `8388608`, about 8MB per session)
- `MAX_RECORDING_SECONDS` (default `30`, checked from decoded audio duration)

## CORS For Frontend

When frontend runs on `http://localhost:8080` and backend on `http://localhost:8000`, CORS must be enabled for browser fetch to `/history` and `/export/markdown`.

Current backend CORS config:

- Allowed origins:
  - `http://localhost:8080`
  - `http://127.0.0.1:8080`
  - plus any `CORS_ORIGINS` entries
- Allowed methods: `GET`, `DELETE`, `OPTIONS`
- Allowed headers: `Content-Type`

Local dev expansion example:

```powershell
$env:CORS_ORIGINS="http://localhost:8080,http://127.0.0.1:8080"
```

## History And AI Boundary

- History is for user review, markdown export and evaluation metrics.
- AI correction (including future Xiaomi integration) must default to current `raw_text` + hotwords + correction mode.
- AI correction must not read full history by default.
- If short recent context is added later, limit to 1-3 recent short items with length caps.

Supported engine values:

- `mock`
- `faster_whisper` (wired; requires model/runtime dependencies)
- `xiaomi_api` (placeholder only, not wired yet)

faster-whisper config:

- `FASTER_WHISPER_MODEL` (default: `base`)
- `FASTER_WHISPER_DEVICE` (default: `cpu`)
- `FASTER_WHISPER_COMPUTE_TYPE` (default: `int8`)

### System Dependencies

When `ASR_ENGINE` is set to `faster_whisper`, the backend relies on the `ffmpeg` executable to robustly decode incoming webm streams into 16kHz raw PCM data (bypassing PyAV container issues). 

- **Requirement**: `ffmpeg` (the executable binary) must be available.
- **Resolution Path**: The backend first tries `FFMPEG_BINARY`, then system `PATH`, then local `ffmpeg.exe`/`bin/ffmpeg.exe`. Each candidate must pass a `-version` health probe. If all fail, backend falls back to bundled `imageio-ffmpeg` binary.

Enable real faster-whisper recognition:

```powershell
$env:ASR_ENGINE="faster_whisper"
$env:FASTER_WHISPER_MODEL="base"
$env:FASTER_WHISPER_DEVICE="cpu"
$env:FASTER_WHISPER_COMPUTE_TYPE="int8"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If model/runtime/ffmpeg/audio decode fails, API returns `ASR_ENGINE_ERROR`.

If session audio bytes exceed `MAX_AUDIO_BYTES`, API returns `AUDIO_TOO_LARGE`.

If decoded audio duration exceeds `MAX_RECORDING_SECONDS`, API returns `CONFIG_ERROR`.
