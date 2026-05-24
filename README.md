# VoiceFlow Input

VoiceFlow Input is a Web MVP for voice input:

`browser recording -> WebSocket -> FastAPI -> ASR -> normalized final text -> history/export`

Current backend supports:

- `GET /health`
- `WS /ws/transcribe` (mock + faster-whisper)
- `GET /history`, `DELETE /history`
- `GET /export/markdown`
- optional `POST /ai/meeting-summary` (Xiaomi MiMo text-only summary)

## Quick Start

```powershell
cd D:\qiniu\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Detailed backend config, protocol, and test commands are in [backend/README.md](/D:/qiniu/backend/README.md).

## Notes

- Default mode is record-then-transcribe (not token-by-token realtime ASR).
- Experimental segment streaming exists and is disabled by default.
- API keys are backend-only environment variables; frontend never receives keys.
- Raw audio is not saved in history.
- No third-party source code is vendored.

## UI Redesign & Frontend Updates (PR Notes)

The frontend Vue application has undergone a significant UI/UX redesign to transition from a dark/glassmorphism aesthetic to a clean, modern, and light theme. 

**Key Design Changes:**
- **Global Theme Re-architecture:** Updated `main.css` to adopt a crisp, light theme with a warm cream background (`#F9F8F1`) to provide a sleek, cohesive experience.
- **Enhanced Typography & Layout:**
  - Removed the restrictive `680px` max-width constraint on the app container, allowing modules to stretch horizontally for a wider, modern layout.
  - Implemented elegant typography for main headings.
  - Replaced placeholder UI elements with functional, product-relevant copy (e.g., "Voice-to-text AI", "Structured notes", "Meeting minutes").
- **Component Restyling:**
  - **Transcript Container:** Expanded horizontally and adjusted to an optimal height. Redesigned with a clean white background, `24px` border radius, and subtle shadows.
  - **Record Button:** Redesigned into a distinct purple pill with a bold black border and custom transition effects. Added keyboard shortcut hints (`[control]`) for better accessibility.
  - **Meeting Agent & History Panels:** Synchronized with the light theme, adopting the same rounded white card style to ensure visual consistency.
- **Zero Backend Disruption:** All visual improvements were executed purely via HTML/CSS layout restructuring in `App.vue` and `main.css`. No Vue `<script setup>` logic, WebSocket connections, or backend integrations were modified, ensuring 100% functional stability.
