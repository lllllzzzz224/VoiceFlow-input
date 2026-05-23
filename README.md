# VoiceFlow Input

VoiceFlow Input is a Web MVP for voice-to-text input:

`browser recording -> WebSocket -> FastAPI -> ASR -> postprocess -> history/export`

Current backend includes:

- `/ws/transcribe` (mock + faster-whisper)
- `/history` and `/export/markdown`
- optional `/ai/meeting-summary` powered by Xiaomi MiMo (text-only enhancement)

## Backend Quick Start

```powershell
cd D:\qiniu\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Optional MiMo Meeting Summary

This feature is optional. If not configured, ASR and history/export still work normally.

```powershell
$env:AI_MEETING_SUMMARY_ENABLED="true"
$env:XIAOMI_API_KEY="your-local-api-key"
$env:XIAOMI_API_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
$env:XIAOMI_MODEL="MiMo-V2.5"
```

Security notes:

- API key is read only on backend from environment variables.
- Frontend never receives API key.
- Raw audio is not persisted in history.
- No third-party source code is vendored into this repository.
