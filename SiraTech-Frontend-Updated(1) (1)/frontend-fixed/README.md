# SiraTech Frontend — Backend-Compatible Version

This frontend is a clean React + Vite client matched to the Flask backend in `sirategide-backend`.

## Features
- Real backend TTS through `POST /api/tts` (no browser speech fallback, so failures are visible).
- English/Arabic voice switching.
- AI Guide chat through `POST /api/guide/chat`.
- Hidden Gem image analysis through `POST /api/vision/analyze`.
- See the Past through `/api/history/...`.
- Heritage Passport through `/api/gamification/...`.
- Uses the backend's actual landmark id `lm-albalad`.

## Run

1. Install Node.js.
2. Run `npm install`.
3. Copy `.env.example` to `.env`.
4. For separate local servers, keep:

   `VITE_API_BASE_URL=http://127.0.0.1:5000/api`

5. Start the backend first.
6. Run `npm run dev`.
7. Open the Vite URL shown in the terminal.

For deployment where the frontend is served from the same origin as the backend, the API base can be left empty and the app will use `/api`.

## Important
The Gemini API key belongs only in the backend `.env`. Never put `GEMINI_API_KEY` in this frontend project.
