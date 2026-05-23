# STATE_MATRIX

## Purpose

This document defines how browser, WebSocket, backend, ASR, postprocessing, history and export states map to user-facing UI.

## Priority Order

1. hard failure
2. microphone or browser permission failure
3. WebSocket connection failure
4. missing/empty audio
5. ASR failure or timeout
6. postprocess / AI correction fallback
7. history/export fallback
8. normal success

## Matrix

| Module State | Frontend Display | User Action | Transcript Usable | Notes |
|---|---|---|---|---|
| `idle` | Ready to record | click record | no | default state |
| `recording` | Recording indicator | click stop | no | disable duplicate start |
| `sending` | Sending audio | wait | no | audio chunks are being sent |
| `transcribing` | Recognizing speech | wait / retry if stuck | no | backend is processing |
| `MIC_PERMISSION_DENIED` | Browser microphone permission required | allow permission / retry | no | frontend-only failure |
| `MIC_DEVICE_NOT_FOUND` | No microphone found | connect device / retry | no | frontend-only failure |
| `WEBSOCKET_CONNECT_FAILED` | Backend connection failed | start backend / retry | no | use friendly message |
| `CONFIG_ERROR` | Protocol/config error | retry / report issue | no | backend stable error shape |
| `NO_SPEECH_DETECTED` | No speech detected | record again | no | no empty transcript success |
| `ASR_TIMEOUT` | Recognition timed out | retry / switch engine | no | optional fallback |
| `ASR_ENGINE_ERROR` | Recognition failed | retry / use mock/fallback | no | no fake transcript |
| raw text available, postprocess failed | Raw transcript with warning | copy raw / retry cleanup | yes, with warning | keep raw text visible |
| AI correction unavailable | Local transcript shown | continue / retry AI | yes | Xiaomi failure must not block local result |
| final text ready | Text ready | copy / save / export | yes | normal success |
| history write failed | Transcript ready, history warning | copy/export manually | yes | history does not block transcript |
| export failed | Export error, transcript remains | retry export / copy | yes | do not lose text |

## UI Rules

1. Hard failures outrank transcript quality.
2. Missing audio cannot be shown as successful recognition.
3. Empty transcript must not be saved or exported as success.
4. WebSocket connection state must be visible.
5. Backend error messages must be user-friendly and must not show stack traces.
6. Raw debug fields are never primary user proof.
7. Do not show raw enum tokens in user-facing UI unless inside a developer/debug panel.

## Product Rules

1. Browser recording is the MVP input path.
2. WebSocket mock mode is valid for integration tests and frontend development.
3. `faster-whisper` is the primary real ASR path.
4. Xiaomi API is optional enhancement/fallback and cannot be required for demo.
5. Hotword corrections must not silently change unrelated words.
6. Local audio should not be persisted unless the user explicitly enables it.
7. Evaluation metrics must distinguish frontend recording time, WebSocket/ASR latency and postprocess time when possible.

## AI Rules

If Xiaomi API or another LLM-based corrector is used:

1. It must not invent content not present in the transcript.
2. It must not recalculate authoritative numbers.
3. It must expose uncertainty as warning, not silent rewrite.
4. Provider failure must fall back to rule-based postprocessing or raw transcript.
5. API keys and provider debug payloads must not appear in normal UI or logs.
