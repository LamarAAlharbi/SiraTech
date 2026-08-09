"""
All TTS (text-to-speech) provider integration lives in this file. Nothing
outside this module talks to a TTS vendor directly — routes and other
services only ever call `synthesize_speech()` below. This mirrors the
isolation pattern used by gemini_service.py and vision_service.py, and is
what makes the provider swappable: adding another vendor later means adding
one function here and one line in `_PROVIDERS`, not touching the route.

Real provider: Gemini TTS ("gemini")
-------------------------------------
The default real provider is Gemini's native text-to-speech model, via the
same `google-genai` SDK (already a dependency for chat/vision) and the same
`GEMINI_API_KEY` already used elsewhere in this app — no new package and no
second credential to provision. It supports natural, human-like speech in
both Arabic and English. Set `TTS_PROVIDER=gemini` to enable it; leave it
unset/`none` to keep using the silent dev fallback (e.g. for offline tests
or before a key is available).

To add a different real provider later:
  1. Write `_synthesize_<provider>(text, language, voice)` below, returning
     the same shape as `_synthesize_fallback` (see its docstring).
  2. Read that provider's credentials from `current_app.config` (add the
     env vars to Config + .env.example) — never hard-code them, never put
     them in the returned dict, and never let a raw provider exception
     (which could embed a key or request URL) bubble past this module.
  3. Register it in `_PROVIDERS` under the name ops will set `TTS_PROVIDER`
     to.
"""

import io
import struct
import wave

from flask import current_app

# The Google GenAI SDK is imported lazily/defensively, exactly like
# vision_service.py: importing this module must never fail just because
# the package (or network) isn't available in a given environment — the
# "gemini" provider raises a clean TTSServiceError instead, and it keeps
# this module testable without the real SDK installed.
try:
    from google import genai
    from google.genai import types as genai_types

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when SDK truly missing
    genai = None
    genai_types = None
    _SDK_AVAILABLE = False


class TTSServiceError(Exception):
    """Raised for any TTS failure: an unconfigured/unimplemented provider, or an upstream API error."""


LANGUAGE_NAMES = {
    "ar": "Arabic",
    "en": "English",
}

_FALLBACK_SAMPLE_RATE_HZ = 16000
_FALLBACK_DURATION_SECONDS = 1.0


def _synthesize_fallback(text, language, voice):
    """
    Dev fallback used whenever TTS_PROVIDER is "none" (the default) or
    unset. No real speech is synthesized — instead this returns a short,
    silent, but genuinely valid WAV clip, so the frontend's audio-player
    integration can be built and tested end-to-end before any TTS vendor
    is selected or credentialed. `text` and `voice` are accepted (and
    unused) purely so this function has the same signature as a real
    provider would.

    Returns:
        dict: {
            "audio_bytes": bytes,   # raw audio file bytes
            "mime_type": str,       # e.g. "audio/wav"
            "provider": "none",
            "voice": str,
        }
    """
    n_frames = int(_FALLBACK_SAMPLE_RATE_HZ * _FALLBACK_DURATION_SECONDS)
    silence = struct.pack("<%dh" % n_frames, *([0] * n_frames))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(_FALLBACK_SAMPLE_RATE_HZ)
        wav_file.writeframes(silence)

    return {
        "audio_bytes": buffer.getvalue(),
        "mime_type": "audio/wav",
        "provider": "none",
        "voice": voice or f"dev-silent-{language}",
    }


# Gemini TTS streams raw 16-bit little-endian PCM at this fixed sample
# rate, mono. See https://ai.google.dev/gemini-api/docs/speech-generation
_GEMINI_TTS_SAMPLE_RATE_HZ = 24000
_GEMINI_TTS_SAMPLE_WIDTH_BYTES = 2
_GEMINI_TTS_CHANNELS = 1

# Prebuilt Gemini voice names (https://ai.google.dev/gemini-api/docs/speech-generation#voices).
# The model auto-detects language from the input text, so the same voice
# works for both Arabic and English; TTS_DEFAULT_VOICE_AR / _EN just let
# ops pick which prebuilt voice sounds best for each language by default.
_GEMINI_VALID_VOICES = {
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
}


def _wrap_pcm_as_wav(pcm_bytes):
    """Wrap raw PCM samples from Gemini TTS in a standard WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(_GEMINI_TTS_CHANNELS)
        wav_file.setsampwidth(_GEMINI_TTS_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(_GEMINI_TTS_SAMPLE_RATE_HZ)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def _gemini_client():
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise TTSServiceError("GEMINI_API_KEY is not configured on the server.")

    if not _SDK_AVAILABLE:
        raise TTSServiceError(
            "The google-genai package is not installed. Run: pip install -r requirements.txt"
        )

    try:
        # api_key is passed straight into the SDK client and never stored,
        # logged, or included in any value this module returns.
        return genai.Client(api_key=api_key)
    except Exception as exc:
        raise TTSServiceError(f"Failed to initialize the Gemini client: {exc}") from exc


def _synthesize_gemini(text, language, voice):
    """
    Real TTS provider backed by Gemini's native speech-generation model.

    Returns the same shape documented on `_synthesize_fallback`, with
    `provider` set to "gemini" and real, audible speech in `audio_bytes`.
    """
    client = _gemini_client()
    model_name = current_app.config.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

    voice_name = voice if voice in _GEMINI_VALID_VOICES else "Kore"
    language_name = LANGUAGE_NAMES.get(language, "English")

    # Gemini TTS speaks whatever language the input text is naturally
    # written in; the explicit instruction just pins that behavior so a
    # short or ambiguous phrase can't drift into the wrong language.
    prompt = f"Say the following in {language_name}, in a natural, clear voice: {text}"

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            ),
        )
    except Exception as exc:
        # Normalized into one clean, typed error so nothing raw (including
        # the API key) ever leaks past this module.
        raise TTSServiceError(f"Gemini TTS request failed: {exc}") from exc

    try:
        candidate = response.candidates[0]
        inline_data = candidate.content.parts[0].inline_data
        pcm_bytes = inline_data.data
    except (AttributeError, IndexError, TypeError) as exc:
        raise TTSServiceError("Gemini TTS returned no audio data.") from exc

    if not pcm_bytes:
        raise TTSServiceError("Gemini TTS returned empty audio data.")

    return {
        "audio_bytes": _wrap_pcm_as_wav(pcm_bytes),
        "mime_type": "audio/wav",
        "provider": "gemini",
        "voice": voice_name,
    }


# Looked up by the TTS_PROVIDER config value. "none" is the silent dev
# fallback; "gemini" is the real, production-capable speech provider.
_PROVIDERS = {
    "none": _synthesize_fallback,
    "gemini": _synthesize_gemini,
}


def _default_voice(language):
    if language == "ar":
        return current_app.config.get("TTS_DEFAULT_VOICE_AR", "default-ar")
    return current_app.config.get("TTS_DEFAULT_VOICE_EN", "default-en")


def synthesize_speech(text, language, voice=None):
    """
    Synthesize speech audio for `text` in `language` using whichever
    provider is configured via the TTS_PROVIDER env var. Falls back to a
    dev-only silent clip when no provider is configured.

    Args:
        text: the text to speak (already length-validated by the caller).
        language: "ar" or "en".
        voice: optional vendor-specific voice name/id. Falls back to
            TTS_DEFAULT_VOICE_AR/EN when omitted.

    Returns:
        dict: {
            "audio_bytes": bytes,
            "mime_type": str,      # e.g. "audio/wav" or "audio/mpeg"
            "provider": str,       # "none" for the dev fallback
            "voice": str,
            "fallback": bool,      # True whenever "none" served the request
        }

    Raises:
        TTSServiceError: if TTS_PROVIDER names a provider not implemented
            in this module, or the upstream provider call fails. Callers
            should map this to a clean 503 — never let it bubble up as a
            raw exception (which could embed a credential or request URL).
    """
    provider_name = (current_app.config.get("TTS_PROVIDER") or "none").strip().lower()
    provider_fn = _PROVIDERS.get(provider_name)

    if provider_fn is None:
        raise TTSServiceError(
            f"TTS_PROVIDER is set to '{provider_name}', which isn't implemented in "
            "tts_service.py yet. Implement a _synthesize_<provider> function and "
            "register it in _PROVIDERS, or set TTS_PROVIDER=none to use the dev fallback."
        )

    voice = voice or _default_voice(language)

    try:
        result = provider_fn(text, language, voice)
    except TTSServiceError:
        raise
    except Exception as exc:
        # Normalizes any provider-specific failure (auth, network, quota,
        # unsupported voice/language, etc.) into one clean, typed error.
        raise TTSServiceError(f"TTS request failed: {exc}") from exc

    result["fallback"] = provider_name == "none"
    return result
