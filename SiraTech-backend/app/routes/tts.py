"""
POST /api/tts — text-to-speech.

Response format for the frontend
---------------------------------
This endpoint returns JSON, not a raw audio stream, so it can carry
metadata (provider, voice, whether this is the dev fallback) alongside the
audio in one response:

    {
      "audio_base64": "UklGRi...",   # base64-encoded audio file bytes
      "mime_type": "audio/wav",      # MIME type of the decoded bytes
      "provider": "none",            # "none" = dev fallback (see below)
      "voice": "dev-silent-en",
      "language": "en",
      "fallback": true               # true = no real TTS provider is
                                      # configured; audio is a silent clip
    }

To play it in a browser, decode the base64 and either build a data URL or
a Blob, e.g.:

    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "...", language: "en" }),
    });
    const { audio_base64, mime_type } = await res.json();
    const audio = new Audio(`data:${mime_type};base64,${audio_base64}`);
    audio.play();

For longer clips, prefer decoding to a Blob (via `atob` + `Uint8Array`) and
`URL.createObjectURL` over a data URL, to avoid building a huge string.

Until the team configures a real TTS_PROVIDER, `fallback` will always be
`true` and the audio will be a short silent clip — enough to build and test
the playback UI, but not real speech.
"""

import base64

from flask import Blueprint, current_app, jsonify, request

from app.errors import ServiceUnavailableError
from app.services import tts_service
from app.services.tts_service import TTSServiceError
from app.utils.validation import get_body_str, get_json_body, require_body_str, require_language

tts_bp = Blueprint("tts", __name__, url_prefix="/api")


@tts_bp.post("/tts")
def synthesize():
    body = get_json_body(request)

    max_length = current_app.config.get("TTS_MAX_TEXT_LENGTH", 1000)
    text = require_body_str(body, "text", max_length=max_length)
    language = require_language(body, "language")
    voice = get_body_str(body, "voice")

    try:
        result = tts_service.synthesize_speech(text=text, language=language, voice=voice)
    except TTSServiceError as exc:
        raise ServiceUnavailableError(
            "The text-to-speech service is temporarily unavailable. Please try again shortly.",
            details={"reason": str(exc)},
        ) from exc

    audio_base64 = base64.b64encode(result["audio_bytes"]).decode("ascii")

    return jsonify(
        {
            "audio_base64": audio_base64,
            "mime_type": result["mime_type"],
            "provider": result["provider"],
            "voice": result["voice"],
            "language": language,
            "fallback": result["fallback"],
        }
    )
