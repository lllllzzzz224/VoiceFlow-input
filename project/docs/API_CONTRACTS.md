# API_CONTRACTS

## Purpose

This project is a Web app first. Contracts define stable shapes between browser frontend, FastAPI backend, ASR adapters, optional AI correction, history and export.

## Contract Rules

1. Backend response schema is source of truth for frontend state.
2. Existing fields cannot be renamed or removed without versioning.
3. New fields may be appended when backward compatible.
4. Error responses must keep a stable shape.
5. Frontend must not rely on provider-specific debug fields.
6. Xiaomi API credentials must never appear in request logs, history rows, README examples or committed config.

## Standard Result Shape

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

## Standard Error Shape

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": {}
  },
  "meta": {}
}
```

## Enums

### FrontendState

```text
idle
recording
sending
transcribing
done
error
```

### WebSocketMessageType

```text
start
audio_chunk
audio_segment
end
ping
ack
pong
partial_transcription_result
partial_error
transcription_result
error
```

### ErrorCode

```text
MIC_PERMISSION_DENIED
MIC_DEVICE_NOT_FOUND
VALIDATION_ERROR
NO_SPEECH_DETECTED
AUDIO_CAPTURE_ERROR
AUDIO_TOO_LARGE
ASR_ENGINE_ERROR
ASR_TIMEOUT
POSTPROCESS_ERROR
AI_PROVIDER_ERROR
CONFIG_ERROR
EXPORT_ERROR
UNKNOWN_ERROR
```

## POST /ai/meeting-summary

Request:

```json
{
  "transcript": "string",
  "mode": "minutes",
  "include_original": true
}
```

Success response:

```json
{
  "success": true,
  "data": {
    "summary_markdown": "string",
    "provider": "xiaomi_mimo",
    "model": "MiMo-V2.5",
    "mode": "minutes"
  },
  "error": null,
  "meta": {
    "latency_ms": 1200,
    "ai_enabled": true,
    "ai_used": true
  }
}
```

Failure response example:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "CONFIG_ERROR",
    "message": "AI meeting summary is not configured.",
    "details": {}
  },
  "meta": {
    "ai_enabled": false,
    "ai_used": false
  }
}
```

### AsrEngine

```text
faster_whisper
xiaomi_api
whisper_cpp
vosk
sherpa_onnx
mock
```

## GET /health

Response:

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

Rules:

1. `/health` must not require model downloads or provider credentials.
2. `/health` must expose selected ASR engine but no secrets.

## WebSocket /ws/transcribe

### Client Start Message

```json
{
  "type": "start",
  "session_id": "local-demo",
  "format": "webm",
  "sample_rate": 16000,
  "channels": 1,
  "language": "zh",
  "hotwords": ["七牛云", "Kodo", "MCP"]
}
```

Rules:

1. `type=start` begins a session.
2. `sample_rate`, `channels`, `language` and `hotwords` are optional in the first mock flow but should remain stable extension points.
3. API keys must not be sent from frontend.
4. `streaming_mode` is optional. Default is full session mode. `streaming_mode=segment` is experimental and controlled by backend config.

### Client Audio Chunk

Preferred MVP transport:

```text
binary websocket message containing an audio chunk
```

JSON fallback:

```json
{
  "type": "audio_chunk",
  "chunk_base64": "BASE64_AUDIO_BYTES"
}
```

Rules:

1. Binary chunks are preferred for browser `MediaRecorder` integration.
2. JSON base64 chunks are allowed for simple tests.
3. Backend must append chunks until `end`.

### Client Audio Segment (Experimental)

```json
{
  "type": "audio_segment",
  "segment_index": 1,
  "chunk_base64": "BASE64_WEBM_SEGMENT",
  "is_final": false
}
```

Rules:

1. Only valid when `streaming_mode=segment`.
2. Each `audio_segment` payload should be a complete segment blob.
3. Segment failure returns `partial_error` without forcing socket close.

### Client End Message

```json
{
  "type": "end"
}
```

Rules:

1. `end` triggers transcription.
2. Empty audio returns `NO_SPEECH_DETECTED`.
3. The backend may close the WebSocket after final result.

### Server Ack Message

```json
{
  "type": "ack",
  "result": {
    "success": true,
    "data": {
      "event": "start_received",
      "sample_rate": 16000,
      "channels": 1
    },
    "error": null,
    "meta": {
      "time": "2026-05-23T00:00:00+00:00"
    }
  }
}
```

### Server Result Message

Current backend envelope:

```json
{
  "type": "transcription_result",
  "result": {
    "success": true,
    "data": {
      "raw_text": "这是一段模拟转写文本",
      "segments": [
        {
          "start_ms": 0,
          "end_ms": 1200,
          "text": "这是一段模拟转写文本"
        }
      ],
      "engine": "mock",
      "latency_ms": 120
    },
    "error": null,
    "meta": {
      "model": "mock-v1",
      "cost_cents": 0,
      "bytes_received": 4096,
      "decode_ms": 0,
      "asr_ms": 1,
      "postprocess_ms": 0,
      "total_ms": 2,
      "audio_duration_ms": 250,
      "model_cached": true,
      "time": "2026-05-23T00:00:00+00:00"
    }
  }
}
```

Rules:

1. Frontend should prefer `message.result.data.final_text` when present, and fallback to `raw_text`.
2. `engine` and `latency_ms` are required for evaluation.
3. `cost_cents` must be `0` for local/mock inference or estimated for cloud calls.
4. Existing `type=transcription_result` must not be renamed without updating frontend and tests together.

Additional meta fields:

- `decode_ms`
- `asr_ms`
- `postprocess_ms`
- `total_ms`
- `audio_duration_ms`
- `model_cached`
- `audio_quality`

### Server Error Message

```json
{
  "type": "transcription_result",
  "result": {
    "success": false,
    "data": null,
    "error": {
      "code": "NO_SPEECH_DETECTED",
      "message": "No audio received.",
      "details": {}
    },
    "meta": {}
  }
}
```

Rules:

1. Error shape is stable.
2. Do not expose stack traces or provider secrets.
3. Frontend must show user-friendly messages.

## Postprocess Contract

Request:

```json
{
  "raw_text": "qi niu yun Kodo",
  "hotword_map": {
    "qi niu yun": "七牛云",
    "Kodo": "Kodo"
  },
  "punctuation_enabled": true,
  "spacing_normalization_enabled": true,
  "ai_correction_enabled": false
}
```

Response:

```json
{
  "success": true,
  "data": {
    "final_text": "七牛云 Kodo。",
    "applied_corrections": [
      {
        "from": "qi niu yun",
        "to": "七牛云",
        "type": "hotword"
      }
    ],
    "warning": null
  },
  "error": null,
  "meta": {
    "ai_provider": null
  }
}
```

Rules:

1. Postprocessor must not invent new semantic content.
2. AI correction is optional and must have fallback.
3. Hotword replacement must be inspectable.

## History Item Contract

```json
{
  "id": "hist_001",
  "created_at": "2026-05-23T00:00:00+08:00",
  "raw_text": "string",
  "final_text": "string",
  "latency_ms": 850,
  "audio_duration_ms": 3200,
  "decode_ms": 120,
  "asr_ms": 610,
  "postprocess_ms": 3,
  "total_ms": 745,
  "engine": "faster_whisper",
  "success": true,
  "error_code": null
}
```

`GET /history` supports query params:

- `limit` (default `50`, min `1`, max `200`)
- `success_only` (default `false`)

## Markdown Export Contract

```json
{
  "title": "VoiceFlow Input Export",
  "created_at": "2026-05-23T00:00:00+08:00",
  "items": [
    {
      "final_text": "string",
      "engine": "mock",
      "latency_ms": 120
    }
  ]
}
```

Rules:

1. Markdown export must use transcript text, not raw debug data.
2. Export should include timestamp and engine metadata.
3. Export failure must not remove transcript from UI.
