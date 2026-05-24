# VoiceFlow Input - Frontend (Vue 3)

This is the Vue 3 frontend application for the VoiceFlow Input project. It provides a sleek, modern, and user-friendly interface for voice-to-text transcription, featuring both standard and experimental quasi-real-time streaming modes.

## Features
- **Clean Light Theme**: A warm, polished aesthetic with modern typography and spacious layouts.
- **Record-then-Transcribe**: Standard reliable WebSocket audio streaming logic.
- **Segment Streaming (Experimental)**: Optional toggle to send 2.5s chunks of audio sequentially for real-time partial text updates.
- **Meeting Minutes Agent**: Integrated with the backend AI summary generation.
- **History & Markdown Export**: Easy access to previous transcriptions and seamless markdown exports.
- **Fast / Accurate ASR Modes**: Frontend supports selecting between `fast` (base model) and `accurate` (small model). The mode is sent via WebSocket start messages. Note: the first use of the accurate mode may take longer as the backend lazy-loads the model. The frontend strictly delegates model management to the backend (no model saving, no API keys, no env modifications).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

## Architecture Notes
- All WebSocket state management and segment streaming logic are housed in `src/composables/useWebSocket.js`.
- The main recording interface, history logs, and AI Agent interactions are managed in `src/App.vue`.
- Styles are heavily centralized in `src/assets/main.css` to allow for easy theme transitions without disrupting functional Vue components.
