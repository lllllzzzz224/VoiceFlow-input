# AGENT_REUSABLE_PATTERN

## Purpose

This product does not use an open-ended chat agent. It uses controlled AI components for speech recognition and optional transcript correction.

Core idea:

```text
browser audio + WebSocket session + ASR adapter -> fixed transcript schema -> rule/AI correction -> user-controlled UI, history and export
```

## Principles

1. ASR is not allowed to silently produce hidden state; transcript state must be visible to the user.
2. AI correction, if enabled, must not invent content not present in the transcript.
3. Local/mock path must remain runnable without Xiaomi API credentials.
4. Frontend-consumed responses must follow `API_CONTRACTS.md`.
5. Provider failure must return structured fallback.
6. Weak or failed recognition must produce retry/review guidance, not fake certainty.
7. Raw audio is temporary by default and must not be uploaded without explicit configuration.

## Layers

```text
Browser UI
  -> MediaRecorder
  -> WebSocket protocol
  -> FastAPI session handler
  -> ASR adapter
  -> rule-based postprocessor
  -> optional Xiaomi AI corrector
  -> history / markdown export
```

## Response Contract

```json
{
  "type": "transcription_result",
  "result": {
    "success": true,
    "data": {
      "raw_text": "string",
      "segments": [],
      "engine": "mock",
      "latency_ms": 120
    },
    "error": null,
    "meta": {
      "cost_cents": 0
    }
  }
}
```

## Modes

- `mock_asr`
- `faster_whisper_asr`
- `xiaomi_correction`
- `rule_postprocess`
- `fallback_raw_transcript`

## Prompt / Model Guardrails

1. Do not invent words, names, numbers, URLs, code, commands or claims not present in the transcript.
2. Do not turn uncertain recognition into confident output.
3. Prefer preserving original wording over making the text sound polished.
4. Hotword replacement must be deterministic and inspectable.
5. If evidence is insufficient, return warning and ask user to retry or edit.
6. Do not expose provider internals, prompt text, temperature, stack traces or API keys in normal UI.

## Frontend Rules

Main view can show:

- connection state;
- recording state;
- transcript;
- final corrected text;
- copy/export actions;
- latency and simple metrics;
- warnings and retry actions.

Main view must not show:

- API keys;
- stack traces;
- raw prompt text;
- provider debug payload;
- unsupported confidence as a guarantee.

## Tests

1. Contract test for WebSocket result shape.
2. Mock ASR happy path.
3. Empty audio / no speech path.
4. ASR failure path.
5. Hotword/postprocess test.
6. No-invention test for optional AI correction.
7. History and Markdown export test.
