"""
Tests for POST /api/guide/chat.

These tests never make a real Gemini API call — they mock
app.services.gemini_service.get_landmark_answer (and, for one test,
simulate it raising GeminiServiceError) so the suite runs fully offline
and without a GEMINI_API_KEY.
"""

from unittest.mock import patch

from app.services.gemini_service import GeminiServiceError

CHAT_URL = "/api/guide/chat"

FAKE_GEMINI_RESULT = {
    "answer": "Hegra was Saudi Arabia's first UNESCO World Heritage Site, carved by the Nabataeans over two thousand years ago.",
    "short_answer_for_speech": "Hegra is Saudi Arabia's first UNESCO site, carved by the Nabataeans.",
    "language": "en",
    "grounding": {
        "sources": [{"title": "UNESCO World Heritage - Hegra", "uri": "https://whc.unesco.org/en/list/1293/"}],
        "search_queries": ["Hegra UNESCO history"],
    },
}


def _valid_payload(**overrides):
    payload = {
        "landmark_id": "lm-hegra",
        "user_message": "When was this site built?",
        "language": "en",
    }
    payload.update(overrides)
    return payload


@patch("app.services.gemini_service.get_landmark_answer")
def test_chat_success_returns_grounded_answer(mock_get_answer, client):
    mock_get_answer.return_value = dict(FAKE_GEMINI_RESULT)

    resp = client.post(CHAT_URL, json=_valid_payload())

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["answer"] == FAKE_GEMINI_RESULT["answer"]
    assert body["short_answer_for_speech"] == FAKE_GEMINI_RESULT["short_answer_for_speech"]
    assert body["language"] == "en"
    assert body["landmark_id"] == "lm-hegra"
    assert body["grounding"]["sources"][0]["uri"].startswith("https://")

    # Gemini call was scoped to the right landmark/location
    _, kwargs = mock_get_answer.call_args
    assert kwargs["landmark"]["id"] == "lm-hegra"
    assert kwargs["location"]["id"] == "loc-alula"
    assert kwargs["language"] == "en"


@patch("app.services.gemini_service.get_landmark_answer")
def test_chat_supports_arabic(mock_get_answer, client):
    mock_get_answer.return_value = {
        "answer": "الحِجر هو أول موقع سعودي على قائمة التراث العالمي لليونسكو.",
        "short_answer_for_speech": "الحِجر أول موقع سعودي في قائمة اليونسكو.",
        "language": "ar",
        "grounding": None,
    }

    resp = client.post(CHAT_URL, json=_valid_payload(language="ar", user_message="متى بُني هذا الموقع؟"))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["language"] == "ar"
    assert body["grounding"] is None


@patch("app.services.gemini_service.get_landmark_answer")
def test_chat_passes_conversation_context(mock_get_answer, client):
    mock_get_answer.return_value = dict(FAKE_GEMINI_RESULT)
    context = [
        {"role": "user", "content": "Tell me about this place."},
        {"role": "assistant", "content": "It's an ancient Nabataean site."},
    ]

    resp = client.post(CHAT_URL, json=_valid_payload(context=context))

    assert resp.status_code == 200
    _, kwargs = mock_get_answer.call_args
    assert kwargs["conversation_context"] == context


def test_chat_missing_landmark_id_returns_400(client):
    payload = _valid_payload()
    del payload["landmark_id"]
    resp = client.post(CHAT_URL, json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_missing_user_message_returns_400(client):
    payload = _valid_payload()
    del payload["user_message"]
    resp = client.post(CHAT_URL, json=payload)
    assert resp.status_code == 400


def test_chat_invalid_language_returns_400(client):
    resp = client.post(CHAT_URL, json=_valid_payload(language="fr"))
    assert resp.status_code == 400
    body = resp.get_json()
    assert "language" in body["error"]["message"]


def test_chat_invalid_context_shape_returns_400(client):
    resp = client.post(CHAT_URL, json=_valid_payload(context=["not a turn object"]))
    assert resp.status_code == 400


def test_chat_non_json_body_returns_400(client):
    resp = client.post(CHAT_URL, data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_chat_unknown_landmark_returns_404_without_calling_gemini(client):
    with patch("app.services.gemini_service.get_landmark_answer") as mock_get_answer:
        resp = client.post(CHAT_URL, json=_valid_payload(landmark_id="does-not-exist"))
        assert resp.status_code == 404
        mock_get_answer.assert_not_called()


@patch("app.services.gemini_service.get_landmark_answer")
def test_chat_gemini_failure_returns_clean_503(mock_get_answer, client):
    mock_get_answer.side_effect = GeminiServiceError("GEMINI_API_KEY is not configured on the server.")

    resp = client.post(CHAT_URL, json=_valid_payload())

    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    # Clean, user-facing message — not a raw traceback.
    assert "temporarily unavailable" in body["error"]["message"].lower()
