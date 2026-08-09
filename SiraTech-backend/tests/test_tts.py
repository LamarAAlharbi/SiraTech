"""
Tests for POST /api/tts.

The dev fallback provider ("none") involves no network call and no
credentials, so most of these tests exercise it directly — no mocking
needed, unlike the Gemini-backed chat/vision endpoints. One test mocks
app.services.tts_service.synthesize_speech to simulate a configured
provider failing, to check the clean-503 behavior.
"""

import base64
import wave
from io import BytesIO
from unittest.mock import patch

from app.services.tts_service import TTSServiceError

TTS_URL = "/api/tts"


def _valid_payload(**overrides):
    payload = {"text": "Welcome to Hegra.", "language": "en"}
    payload.update(overrides)
    return payload


def _decode_wav(audio_base64):
    raw = base64.b64decode(audio_base64)
    with wave.open(BytesIO(raw), "rb") as wav_file:
        return {
            "n_channels": wav_file.getnchannels(),
            "sample_width": wav_file.getsampwidth(),
            "frame_rate": wav_file.getframerate(),
            "n_frames": wav_file.getnframes(),
        }


def test_tts_dev_fallback_returns_valid_playable_audio(client):
    resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["provider"] == "none"
    assert body["fallback"] is True
    assert body["mime_type"] == "audio/wav"
    assert body["language"] == "en"
    assert body["voice"]

    # The audio is real, decodable WAV data — not just a placeholder string.
    wav_info = _decode_wav(body["audio_base64"])
    assert wav_info["n_channels"] == 1
    assert wav_info["sample_width"] == 2
    assert wav_info["frame_rate"] > 0
    assert wav_info["n_frames"] > 0


def test_tts_supports_arabic(client):
    resp = client.post(TTS_URL, json=_valid_payload(language="ar", text="مرحبا بكم في الحِجر."))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["language"] == "ar"
    assert "ar" in body["voice"]


def test_tts_accepts_optional_voice_override(client):
    resp = client.post(TTS_URL, json=_valid_payload(voice="custom-voice-1"))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["voice"] == "custom-voice-1"


def test_tts_never_exposes_any_key_or_secret(client, app):
    app.config["TTS_API_KEY"] = "super-secret-value-should-never-appear"
    resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 200
    assert "super-secret-value-should-never-appear" not in resp.get_data(as_text=True)


def test_tts_missing_text_returns_400(client):
    payload = _valid_payload()
    del payload["text"]
    resp = client.post(TTS_URL, json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_tts_missing_language_returns_400(client):
    payload = _valid_payload()
    del payload["language"]
    resp = client.post(TTS_URL, json=payload)
    assert resp.status_code == 400


def test_tts_invalid_language_returns_400(client):
    resp = client.post(TTS_URL, json=_valid_payload(language="fr"))
    assert resp.status_code == 400


def test_tts_text_over_limit_returns_400(client, app):
    app.config["TTS_MAX_TEXT_LENGTH"] = 10
    resp = client.post(TTS_URL, json=_valid_payload(text="This text is definitely over ten characters."))
    assert resp.status_code == 400
    body = resp.get_json()
    assert "characters" in body["error"]["message"]


def test_tts_blank_voice_returns_400(client):
    resp = client.post(TTS_URL, json=_valid_payload(voice="   "))
    assert resp.status_code == 400


def test_tts_non_json_body_returns_400(client):
    resp = client.post(TTS_URL, data="not json", content_type="text/plain")
    assert resp.status_code == 400


@patch("app.services.tts_service.synthesize_speech")
def test_tts_provider_failure_returns_clean_503(mock_synthesize, client):
    mock_synthesize.side_effect = TTSServiceError(
        "TTS_PROVIDER is set to 'unknown-vendor', which isn't implemented."
    )

    resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert "temporarily unavailable" in body["error"]["message"].lower()


def test_tts_unimplemented_provider_returns_clean_503(client, app):
    app.config["TTS_PROVIDER"] = "some-vendor-not-yet-wired-up"
    resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"]["code"] == "AI_SERVICE_UNAVAILABLE"


# --- Real "gemini" provider -------------------------------------------------
#
# These never make a real network call — they mock the google-genai client
# returned by tts_service._gemini_client, exactly like test_vision.py mocks
# the Gemini vision client. The suite runs fully offline and without a
# GEMINI_API_KEY.


def _fake_gemini_response(pcm_bytes=b"\x01\x00" * 100):
    part = type("Part", (), {"inline_data": type("InlineData", (), {"data": pcm_bytes})()})()
    content = type("Content", (), {"parts": [part]})()
    candidate = type("Candidate", (), {"content": content})()
    return type("Response", (), {"candidates": [candidate]})()


def test_tts_gemini_provider_returns_real_audio(client, app):
    app.config["TTS_PROVIDER"] = "gemini"
    app.config["GEMINI_API_KEY"] = "test-key"

    with patch("app.services.tts_service._gemini_client") as mock_client_fn:
        mock_client = mock_client_fn.return_value
        mock_client.models.generate_content.return_value = _fake_gemini_response()

        resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["provider"] == "gemini"
    assert body["fallback"] is False
    assert body["mime_type"] == "audio/wav"

    wav_info = _decode_wav(body["audio_base64"])
    assert wav_info["n_channels"] == 1
    assert wav_info["frame_rate"] == 24000
    assert wav_info["n_frames"] > 0


def test_tts_gemini_provider_arabic(client, app):
    app.config["TTS_PROVIDER"] = "gemini"
    app.config["GEMINI_API_KEY"] = "test-key"

    with patch("app.services.tts_service._gemini_client") as mock_client_fn:
        mock_client = mock_client_fn.return_value
        mock_client.models.generate_content.return_value = _fake_gemini_response()

        resp = client.post(TTS_URL, json=_valid_payload(language="ar", text="مرحبا بكم في الحِجر."))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["language"] == "ar"
    assert body["provider"] == "gemini"


def test_tts_gemini_missing_api_key_returns_clean_503(client, app):
    app.config["TTS_PROVIDER"] = "gemini"
    app.config["GEMINI_API_KEY"] = None

    resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert "GEMINI_API_KEY" not in str(body)


def test_tts_gemini_upstream_failure_returns_clean_503_without_leaking_key(client, app):
    app.config["TTS_PROVIDER"] = "gemini"
    app.config["GEMINI_API_KEY"] = "super-secret-value-should-never-appear"

    with patch("app.services.tts_service._gemini_client") as mock_client_fn:
        mock_client = mock_client_fn.return_value
        mock_client.models.generate_content.side_effect = RuntimeError(
            "upstream exploded with key=super-secret-value-should-never-appear"
        )

        resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 503
    assert "super-secret-value-should-never-appear" not in resp.get_data(as_text=True)


def test_tts_gemini_empty_audio_returns_clean_503(client, app):
    app.config["TTS_PROVIDER"] = "gemini"
    app.config["GEMINI_API_KEY"] = "test-key"

    with patch("app.services.tts_service._gemini_client") as mock_client_fn:
        mock_client = mock_client_fn.return_value
        mock_client.models.generate_content.return_value = _fake_gemini_response(pcm_bytes=b"")

        resp = client.post(TTS_URL, json=_valid_payload())

    assert resp.status_code == 503
