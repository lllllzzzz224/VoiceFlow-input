# ACCEPTANCE_CASES

## Purpose

No feature is done until it maps to acceptance evidence. These cases define the minimum verification surface for the Web voice input assistant MVP.

## Case A001: Health Check

Given:

- Backend service is started.

When:

- User or test calls `GET /health`.

Then:

- Backend returns standard success shape.
- Response includes selected ASR engine and version metadata.

Expected UI:

- Frontend can tell the user backend is available.

Expected state:

- `success=true`
- `data.status=ok`

Validation:

- Manual request or automated test.

## Case A002: WebSocket Mock Happy Path

Given:

- Backend is running with mock ASR adapter.
- Browser microphone is available.

When:

- Frontend connects to `/ws/transcribe`.
- Sends `start`.
- Sends one or more audio chunks.
- Sends `end`.

Then:

- Backend returns `type=transcription_result`.
- Result follows standard shape.
- Frontend displays transcript and latency.

Expected UI:

- Recording and transcribing states transition to done.
- Transcript is visible.

Expected state:

- `result.success=true`
- `result.data.engine=mock`
- `result.data.latency_ms` exists

Validation:

- `backend/tests/ws_mock_smoke.py`
- Manual browser recording against mock backend.

## Case A003: Browser Microphone Permission Failure

Given:

- Browser microphone permission is denied.

When:

- User clicks record.

Then:

- Frontend does not open WebSocket recording flow.
- UI explains how to allow microphone access.

Expected UI:

- Permission error message and retry path.

Expected state:

- frontend state `error`

Validation:

- Deny microphone permission in browser.

## Case A004: WebSocket Connection Failure

Given:

- Backend service is not running.

When:

- User clicks record and frontend tries to connect.

Then:

- UI shows backend connection failure.
- No transcript is shown as success.

Expected UI:

- “Start backend service” or equivalent recovery guidance.

Expected state:

- frontend state `error`

Validation:

- Open frontend without backend and attempt recording.

## Case A005: No Audio / No Speech

Given:

- WebSocket connection is established.
- No audio chunk is sent, or audio is empty.

When:

- Client sends `end`.

Then:

- Backend returns `NO_SPEECH_DETECTED`.
- Frontend asks user to record again.

Expected UI:

- No speech detected message.

Expected state:

- `result.success=false`
- `result.error.code=NO_SPEECH_DETECTED`

Validation:

- WebSocket test sends start then end without audio.

## Case A006: Faster-Whisper Transcription

Given:

- `faster-whisper` dependency and model are available.
- Backend is configured to use `faster_whisper`.

When:

- User records a short Chinese or mixed Chinese/English utterance.

Then:

- Backend returns real transcript using the same `transcription_result` envelope.
- Frontend does not need protocol changes.

Expected UI:

- Transcript, engine and latency displayed.

Expected state:

- `result.success=true`
- `result.data.engine=faster_whisper`

Validation:

- Manual or opt-in integration test with model available.

## Case A007: ASR Failure

Given:

- Backend is configured with an unavailable model or ASR engine fails.

When:

- Client sends audio and `end`.

Then:

- Backend returns stable ASR error.
- Frontend shows retry/fallback guidance.

Expected UI:

- Recognition failed message, no fake transcript.

Expected state:

- `result.success=false`
- `result.error.code=ASR_ENGINE_ERROR` or `ASR_TIMEOUT`

Validation:

- Configure invalid model path or mock adapter failure.

## Case A008: Postprocess / Hotword Correction

Given:

- Raw transcript contains words needing punctuation, spacing or hotword correction.

When:

- Postprocessor runs.

Then:

- Final text is cleaned.
- Applied corrections are inspectable when exposed.

Expected UI:

- Cleaned final text is shown.

Expected state:

- `final_text` may be appended without removing `raw_text`.

Validation:

- Fixed test sentences including “七牛云”“Kodo”“MCP”.

## Case A009: Xiaomi AI Correction Fallback

Given:

- Xiaomi API is configured or intentionally unavailable.

When:

- User enables AI correction.

Then:

- If provider succeeds, final text is improved without inventing content.
- If provider fails or key is absent, raw/local transcript remains usable.

Expected UI:

- AI correction status or fallback warning.

Expected state:

- Provider failure does not erase transcript.

Validation:

- Use mock/test key path and missing-key path.

## Case A010: History And Markdown Export

Given:

- User has one or more successful transcript results.

When:

- User opens history or exports Markdown.

Then:

- History includes transcript, engine and latency metadata.
- Markdown export includes transcript content and timestamp.

Expected UI:

- Recent entries visible.
- Export action creates Markdown content or downloadable file.

Expected state:

- History item includes `raw_text`/`final_text`, `engine`, `latency_ms`, `success`.

Validation:

- Manual browser test after multiple recordings.

## Case A011: Open Source Compliance

Given:

- Reference projects are used for research.

When:

- Preparing README and final PRs.

Then:

- Direct dependencies and reference-only projects are listed.
- No third-party source directories, copied README paragraphs or committed model/audio/cache files are present.

Expected UI:

- n/a

Expected state:

- `.gitignore` excludes cache, env, model and temporary audio artifacts.

Validation:

- `rg --files`
- manual README/source review.
