"""
Tests for POST /api/vision/analyze (SiraTech Hidden Gems).

These tests never make a real Gemini API call — they mock
app.services.vision_service.identify_landmark (and, for one test, simulate
it raising VisionServiceError) so the suite runs fully offline and without
a GEMINI_API_KEY.
"""

import io
from unittest.mock import patch

from app.services.vision_service import VisionServiceError

ANALYZE_URL = "/api/vision/analyze"

FAKE_CONFIDENT_RESULT = {
    "identified_name": "Hegra",
    "category": "UNESCO Heritage Site",
    "description": "A Nabataean rock-cut tomb complex with monumental carved facades.",
    "confidence": "high",
    "uncertain": False,
    "language": "en",
}

FAKE_UNCERTAIN_RESULT = {
    "identified_name": None,
    "category": None,
    "description": "The photo shows a sandstone cliff face but no distinguishing man-made features.",
    "confidence": "low",
    "uncertain": True,
    "language": "en",
}


def _fake_image(filename="photo.jpg", content_type="image/jpeg", content=b"\xff\xd8\xff fake jpeg bytes"):
    return (io.BytesIO(content), filename, content_type)


def _post(client, *, image=True, language="en", extra_fields=None, content_type="image/jpeg"):
    data = dict(extra_fields or {})
    if language is not None:
        data["language"] = language
    if image:
        data["image"] = _fake_image(content_type=content_type)
    return client.post(ANALYZE_URL, data=data, content_type="multipart/form-data")


@patch("app.services.vision_service.identify_landmark")
def test_analyze_confident_match_resolves_landmark_id(mock_identify, client):
    mock_identify.return_value = dict(FAKE_CONFIDENT_RESULT)

    resp = _post(client, extra_fields={"landmark_id": "lm-hegra"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["identified_name"] == "Hegra"
    assert body["category"] == "UNESCO Heritage Site"
    assert body["possible_landmark_id"] == "lm-hegra"
    assert body["confidence"] == "high"
    assert body["uncertain"] is False

    # The API key never appears anywhere in the response.
    assert "GEMINI_API_KEY" not in str(body)
    assert "api_key" not in str(body).lower()

    _, kwargs = mock_identify.call_args
    assert kwargs["hint_landmark_name"] == "Hegra (Mada'in Salih)"
    assert kwargs["language"] == "en"


@patch("app.services.vision_service.identify_landmark")
def test_analyze_matches_via_latitude_longitude_without_landmark_id(mock_identify, client):
    mock_identify.return_value = dict(FAKE_CONFIDENT_RESULT)

    # Near AlUla (loc-alula), where lm-hegra lives.
    resp = _post(client, extra_fields={"latitude": "26.6", "longitude": "37.9"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["possible_landmark_id"] == "lm-hegra"


@patch("app.services.vision_service.identify_landmark")
def test_analyze_uncertain_result_returns_no_landmark_id(mock_identify, client):
    mock_identify.return_value = dict(FAKE_UNCERTAIN_RESULT)

    resp = _post(client, extra_fields={"landmark_id": "lm-hegra"})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["identified_name"] is None
    assert body["uncertain"] is True
    assert body["possible_landmark_id"] is None


@patch("app.services.vision_service.identify_landmark")
def test_analyze_supports_arabic(mock_identify, client):
    mock_identify.return_value = {
        "identified_name": "الحِجر",
        "category": "موقع تراث عالمي لليونسكو",
        "description": "مجمع مقابر منحوتة في الصخر.",
        "confidence": "medium",
        "uncertain": False,
        "language": "ar",
    }

    resp = _post(client, language="ar")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["language"] == "ar"


def test_analyze_missing_image_returns_400(client):
    resp = _post(client, image=False)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_missing_language_returns_400(client):
    resp = _post(client, language=None)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_invalid_language_returns_400(client):
    resp = _post(client, language="fr")
    assert resp.status_code == 400


def test_analyze_rejects_disallowed_content_type(client):
    resp = _post(client, content_type="application/pdf")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "image" in body["error"]["message"].lower()


def test_analyze_rejects_oversized_image(client, app):
    app.config["VISION_MAX_IMAGE_BYTES"] = 10  # tiny limit for this test
    resp = _post(client, extra_fields={})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "exceeds" in body["error"]["message"].lower()


def test_analyze_partial_coordinates_returns_400(client):
    resp = _post(client, extra_fields={"latitude": "24.7"})
    assert resp.status_code == 400


def test_analyze_unknown_landmark_id_returns_404_without_calling_vision(client):
    with patch("app.services.vision_service.identify_landmark") as mock_identify:
        resp = _post(client, extra_fields={"landmark_id": "does-not-exist"})
        assert resp.status_code == 404
        mock_identify.assert_not_called()


@patch("app.services.vision_service.identify_landmark")
def test_analyze_vision_service_failure_returns_clean_503(mock_identify, client):
    mock_identify.side_effect = VisionServiceError("GEMINI_API_KEY is not configured on the server.")

    resp = _post(client)

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert "temporarily unavailable" in body["error"]["message"].lower()
    # The underlying reason is available for debugging but never a raw traceback.
    assert "GEMINI_API_KEY" in body["error"]["details"]["reason"]
