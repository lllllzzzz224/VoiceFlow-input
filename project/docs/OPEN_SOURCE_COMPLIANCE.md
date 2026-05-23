# OPEN_SOURCE_COMPLIANCE

## Purpose

This document defines how this project may learn from high-star GitHub repositories without copying code or violating competition integrity rules.

Competition risk:

- The work must be independently completed.
- Code or technical plagiarism can invalidate the submission.
- Code similarity above 50% is treated as plagiarism risk.

## Policy

1. Reference projects are used for architecture, API usage, risk analysis and product boundary decisions.
2. Third-party libraries must be installed through package managers or documented release artifacts when possible.
3. Do not vendor third-party source code into this repository unless there is a documented decision and license review.
4. Do not copy README wording, benchmark tables, screenshots, demo scripts, UI layouts or repository structure.
5. Any reused snippet must be tiny, necessary, licensed, attributed and mentioned in the PR description.
6. PR descriptions must state whether a change is original implementation, dependency integration or reference-inspired design.
7. README must list direct dependencies, optional providers, model sources and reference-only projects.

## Direct Dependency Candidates

| Project | Role | License Note | Usage Rule |
|---|---|---|---|
| FastAPI | Backend HTTP/WebSocket service | Library dependency | Use package API only |
| faster-whisper | Primary ASR backend | MIT | Install package; do not copy `faster_whisper/` source |
| Xiaomi API | Optional cloud fallback or enhancement | Provider terms required | API key in local env only; no key in repo |
| Tauri | Optional later desktop shell | Check Tauri/Rust dependency licenses if used | Only after Web MVP is stable |

## Reference-Only Projects

| Project | What To Learn | What Not To Copy |
|---|---|---|
| openai/whisper | ASR concepts, transcript semantics, model tradeoffs | Model code, README examples, CLI UX, benchmark wording |
| SYSTRAN/faster-whisper | Official API usage, VAD option, adapter boundaries | Package source, benchmark tables, README text |
| ggml-org/whisper.cpp | Offline fallback concept, quantized model strategy, CLI/server idea | C++ examples, shell scripts, README/demo outputs |
| alphacep/vosk-api | Lightweight offline fallback and vocabulary idea | Example app structure, training/service matrix |
| k2-fsa/sherpa-onnx | Future VAD/KWS/streaming direction | Example matrix, large script copies |
| collabora/WhisperLive | Client/server split, model singleton, metrics/VAD module ideas | WebSocket protocol implementation, extension code, README visuals |
| rime/librime | Future native IME boundary and plugin concept | C++ core/plugin code |
| fcitx/fcitx5 | Future Linux IME plugin architecture | Addon skeleton, C++ framework code |
| Tauri ecosystem | Later desktop shell packaging | Starter templates or generated boilerplate copied without review |

## Original Work Boundary

The project-owned implementation should focus on:

- browser recording UI and state machine;
- WebSocket client protocol;
- FastAPI WebSocket session handler;
- ASR adapter interface;
- mock adapter for integration;
- faster-whisper adapter glue;
- optional Xiaomi API correction/fallback glue;
- text postprocessing rules;
- history and Markdown export;
- test harness and benchmark scripts;
- README, demo script and evaluation report.

If the later Tauri shell is implemented, original work should focus on:

- wiring the existing frontend into the shell;
- starting or connecting to the local FastAPI backend;
- packaging configuration;
- optional tray/global shortcut behavior;
- keeping Web mode independently runnable.

## PR Checklist

Each PR should answer:

1. What reference project or dependency influenced this change?
2. Is any third-party code copied? The default answer should be no.
3. Which files are original project implementation?
4. Which dependency APIs are called?
5. What license or provider terms must README mention?
6. How was the change tested?

## Similarity Guard

Before final submission:

1. Search for accidental third-party source directories.
2. Search README for copied paragraphs from reference projects.
3. Check that examples and benchmark numbers are our own or clearly attributed.
4. Ensure API keys and private configs are absent.
5. Ensure `README.md` and PR descriptions explain dependency usage and original feature scope.
