"""
Application configuration.

All values come from environment variables (loaded from .env in run.py).
Nothing sensitive is hard-coded here — only sane local-dev defaults for
non-secret settings.
"""

import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(APP_DIR, "data")


class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))

    # Comma-separated list of allowed frontend origins, e.g.
    # "http://localhost:3000,https://sirategide-frontend.vercel.app"
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    ]

    # Directory containing the seed JSON files. Overridable for tests.
    DATA_DIR = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)

    # Simple API key gate for write-ish/admin use later (optional in prototype).
    # Left unset by default; if set, could be enforced by a decorator.
    API_KEY = os.getenv("API_KEY")

    # Gemini (Google GenAI) — used by app/services/gemini_service.py for the
    # /api/guide/chat endpoint. Never hard-code this; if it's unset the chat
    # endpoint fails cleanly with a 503 rather than crashing the app.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Vision-capable Gemini model used by app/services/vision_service.py for
    # POST /api/vision/analyze (the "Hidden Gems" landmark-recognition
    # feature). Falls back to GEMINI_MODEL if unset — just keep it pointed
    # at a model that accepts image input.
    GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    # Upload constraints enforced by app/utils/validation.py before any
    # image reaches Gemini.
    VISION_MAX_IMAGE_BYTES = int(os.getenv("VISION_MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
    VISION_ALLOWED_MIME_TYPES = tuple(
        t.strip()
        for t in os.getenv("VISION_ALLOWED_MIME_TYPES", "image/jpeg,image/png,image/webp").split(",")
        if t.strip()
    )

    # Text-to-speech (SiraTech TTS) — used by app/services/tts_service.py for
    # POST /api/tts. Two providers are implemented:
    #   - "none"   (default): silent dev fallback, no credentials needed.
    #   - "gemini": real, production-capable speech via the Gemini TTS
    #     model. Reuses GEMINI_API_KEY above — no separate credential.
    # Set TTS_PROVIDER=gemini to enable real speech; leave it "none" for
    # offline dev/tests. TTS_API_KEY/TTS_API_REGION are left in place for a
    # future non-Gemini vendor and are unused by the "gemini" provider.
    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "none")
    TTS_API_KEY = os.getenv("TTS_API_KEY")
    TTS_API_REGION = os.getenv("TTS_API_REGION")  # some vendors need a region/endpoint too
    GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    # Prebuilt Gemini voice names — see
    # https://ai.google.dev/gemini-api/docs/speech-generation#voices
    TTS_DEFAULT_VOICE_EN = os.getenv("TTS_DEFAULT_VOICE_EN", "Kore")
    TTS_DEFAULT_VOICE_AR = os.getenv("TTS_DEFAULT_VOICE_AR", "Kore")
    TTS_MAX_TEXT_LENGTH = int(os.getenv("TTS_MAX_TEXT_LENGTH", "1000"))

    # SiraTech Gamification (XP, discoveries, badges) — see
    # app/services/gamification_repository.py. This is a simple SQLite
    # prototype store, deliberately isolated behind that one module so it
    # can be swapped for a production database later without touching
    # gamification_service.py or the routes. Defaults to a file under
    # instance/ (git-ignored, created on first run) so the dev DB never
    # collides with the read-only seed data in app/data/.
    INSTANCE_DIR = os.path.join(os.path.dirname(APP_DIR), "instance")
    GAMIFICATION_DB_PATH = (
        os.getenv("GAMIFICATION_DB_PATH") or os.path.join(INSTANCE_DIR, "gamification.sqlite3")
    )
