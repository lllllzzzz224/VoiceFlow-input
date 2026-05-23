# VoiceFlow Input Backend (Web MVP)

Minimal backend loop for Web MVP:

`browser audio recording -> WebSocket -> FastAPI -> ASR adapter -> transcription text`

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
      "time": "2026-05-23T00:00:00+00:00"
    }
  }
}
```

### History API

```http
GET /history
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
      "error_code": null
    }
  ],
  "count": 1
}
```

History is stored in local JSON and does not include raw audio.

## Config

Environment variables:

- `ASR_ENGINE` (`mock` by default)
- `MOCK_RESPONSE_TEXT` (`mock transcription` by default)
- `POSTPROCESS_PUNCTUATION_ENABLED` (`true` by default)
- `POSTPROCESS_SPACING_ENABLED` (`true` by default)
- `HOTWORD_MAP_JSON` (JSON object string, optional)
- `HISTORY_FILE_PATH` (`data/history.json` by default)

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
