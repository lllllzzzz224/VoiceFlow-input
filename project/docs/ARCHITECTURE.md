# ARCHITECTURE

## High-Level Flow

```text
browser microphone -> MediaRecorder -> WebSocket -> FastAPI -> ASR adapter -> postprocess / AI correction -> WebSocket result -> UI / history / markdown export
```

## Runtime Shape

- Product form: Web voice input workspace.
- Frontend: browser app in `frontend/`.
- Backend: FastAPI app in `backend/`.
- Transport: WebSocket at `/ws/transcribe`.
- ASR main path: `faster-whisper` adapter.
- Test path: mock adapter.
- Optional enhancement: Xiaomi API adapter for correction or fallback.
- Output: transcript display, copy button, history, Markdown export.
- Later desktop shell: Tauri may wrap the Web frontend and local FastAPI backend after Web MVP is stable.

## Module Boundaries

### Frontend Web App

Responsible for:

- Request microphone permission through browser APIs.
- Record audio with `MediaRecorder`.
- Open WebSocket connection to `ws://localhost:8000/ws/transcribe`.
- Send `start`, audio chunks and `end`.
- Render connection, recording, sending, transcribing, done and error states.
- Display transcript and latency.
- Provide copy, history and Markdown export interactions.

Not responsible for:

- Running ASR inference.
- Holding API keys.
- Reimplementing backend validation.
- Copying UI or code from WhisperLive.

Inputs:

- User record/stop/copy/export actions.
- Microphone stream.
- WebSocket result messages.

Outputs:

- JSON protocol messages.
- Binary audio chunks.
- User-visible transcript states.

Failure behavior:

- Missing microphone permission shows a clear browser permission message.
- WebSocket failure asks the user to start backend service.
- Backend error messages are shown without stack traces.

### WebSocket Protocol Layer

Responsible for:

- Accept one transcription session per WebSocket connection.
- Receive JSON control messages and binary audio chunks.
- Return ack, result and error envelopes.
- Keep response shape stable for frontend and tests.

Not responsible for:

- Persisting long-term history.
- Exposing model internals.
- Sending provider credentials.

Inputs:

- `start` JSON message.
- Binary audio chunks or `audio_chunk` JSON fallback.
- `end` JSON message.

Outputs:

- `ack`
- `transcription_result`
- `error`
- `pong`

Failure behavior:

- Invalid JSON returns `CONFIG_ERROR`.
- Unsupported message type returns `CONFIG_ERROR`.
- Empty audio returns `NO_SPEECH_DETECTED`.
- ASR failure returns `ASR_ENGINE_ERROR`.

### Backend API

Responsible for:

- FastAPI app startup.
- `/health` endpoint.
- `/ws/transcribe` WebSocket endpoint.
- Standard result and error envelope.
- Adapter selection from settings.

Not responsible for:

- Browser audio capture.
- Frontend visual state.
- Shipping third-party ASR source code.

Inputs:

- WebSocket messages.
- Local settings and environment variables.

Outputs:

- Standard JSON responses.
- Transcription result envelopes.

Failure behavior:

- Missing optional API key disables that provider without breaking mock/local mode.
- Missing ASR model returns stable ASR error.

### ASR Adapter Interface

Responsible for:

- Convert received audio bytes to transcript data.
- Normalize engine-specific output into the project contract.
- Report `latency_ms`, `engine`, `segments` and model metadata.

Not responsible for:

- Copying or vendoring third-party engine code.
- UI state management.
- Inventing speech content.

Inputs:

- `audio_bytes`
- `sample_rate`
- `channels`
- optional `language`
- optional `hotwords`

Outputs:

- `raw_text`
- `segments`
- `engine`
- `latency_ms`

Failure behavior:

- Engine failures are converted to standard error shape.
- mock adapter stays available for tests and frontend integration.

Implementation note:

- MVP primary adapter: `faster-whisper` through public Python API.
- Optional cloud/fallback adapter: Xiaomi API through local environment configuration.
- Future fallback candidates: `whisper.cpp` CLI/server, Vosk, sherpa-onnx.
- Do not git clone, vendor or copy third-party ASR project source into this repository.

### Text Postprocessor

Responsible for:

- Add or normalize simple punctuation.
- Apply hotword correction.
- Clean Chinese/English spacing.
- Prepare final text for display and export.

Not responsible for:

- Rewriting the user's intent.
- Inventing content not present in transcript.
- Acting as a general chat assistant.

Inputs:

- Raw transcript.
- Hotword dictionary.
- User settings.

Outputs:

- Final transcript.
- Applied correction list.
- Warning if fallback was used.

Failure behavior:

- If postprocessing fails, return raw transcript with warning.

### Xiaomi API Enhancement

Responsible for:

- Optional transcript correction, punctuation, formatting or fallback.
- Keep provider-specific code behind an adapter.
- Return the same project contract as other backends.

Not responsible for:

- Being the only runnable ASR/correction path.
- Receiving audio/text without explicit user configuration.
- Exposing API keys or provider debug data.

Failure behavior:

- Missing API key disables Xiaomi mode.
- Provider failure falls back to local/raw transcript path.

### History / Export

Responsible for:

- Store recent transcript sessions.
- Track engine, latency and success/error status.
- Export selected transcript/history as Markdown.

Not responsible for:

- Storing raw audio by default.
- Uploading history without explicit user action.

Failure behavior:

- History failure does not block transcription.
- Export failure leaves transcript visible for manual copy.

### Open Source Compliance

Responsible for:

- Keep dependencies and references documented.
- Distinguish direct dependencies from reference-only projects.
- Prevent accidental submission of reference project source.

Not responsible for:

- Pulling high-star projects into this repository.

Rules:

- Use `faster-whisper` as a package dependency, not as copied source.
- Read `WhisperLive`, `whisper.cpp`, `sherpa-onnx` for ideas only.
- README must list dependency and reference boundaries.

### Later Tauri Desktop Shell

Responsible for:

- Wrap the existing Web frontend after Web MVP is stable.
- Start or connect to the local FastAPI backend.
- Package the working Web experience as a desktop app.
- Optionally add tray/global shortcut behavior if time allows.

Not responsible for:

- Rewriting ASR logic.
- Replacing the Web app as the source of truth.
- Introducing native IME integration.
- Pulling third-party desktop/input-method projects into this repository.

Inputs:

- Existing `frontend/` build.
- Existing `backend/` service.
- Local runtime configuration.

Outputs:

- Desktop app shell.
- Same transcript and export behavior as Web MVP.

Failure behavior:

- If Tauri packaging fails, Web version remains the deliverable.
- Desktop failure must not block README/demo for Web MVP.

## Failure Strategy

- microphone failure: frontend displays browser permission or device guidance.
- WebSocket failure: frontend instructs user to start backend and retry.
- no audio: backend returns `NO_SPEECH_DETECTED`.
- ASR failure: backend returns `ASR_ENGINE_ERROR` with stable shape.
- postprocess failure: return raw transcript with warning.
- Xiaomi failure: fallback to local/raw transcript path.
- history/export failure: keep transcript visible and copyable.
