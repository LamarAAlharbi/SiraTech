"""
Exercises the full required SiraTech flow end-to-end against one Flask
test client, in order:

    Map selects Historic Jeddah
      -> guide details (location + landmark)
      -> Gemini Guide (AI chat)
      -> TTS
      -> camera -> vision analysis (Hidden Gems)
      -> historical database / See the Past
      -> XP / badge (gamification)

No real Gemini/TTS credentials are configured in the test environment, so
the AI-backed steps (chat, vision) are expected to fail *cleanly* with a
503 rather than crash or leak anything — that's asserted explicitly. TTS
still succeeds via its built-in dev fallback.

This test also guards two hard requirements from the product brief:
  - no API key/secret ever appears in a response body, and
  - no itinerary/pricing/booking/transportation feature exists.
"""

FORBIDDEN_SCOPE_WORDS = (
    "itinerary",
    "pricing",
    "book a room",
    "booking",
    "transportation",
    "hotel",
)

SECRET_CONFIG_KEYS = ("GEMINI_API_KEY", "TTS_API_KEY", "API_KEY", "TTS_API_REGION")


def _assert_no_secrets_or_forbidden_scope(app, resp):
    body_text = resp.get_data(as_text=True).lower()

    for key in SECRET_CONFIG_KEYS:
        value = app.config.get(key)
        if value:  # only meaningful if a real secret is actually configured
            assert value not in body_text

    for word in FORBIDDEN_SCOPE_WORDS:
        assert word not in body_text, f"forbidden scope word '{word}' leaked into a response"


def test_full_discovery_flow_for_historic_jeddah(app, client):
    # 1. Map selects Historic Jeddah -> location guide (landmarks in Jeddah)
    resp = client.get("/api/v1/guide/locations/loc-jeddah")
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    location_guide = resp.get_json()
    landmark_ids = [lm["id"] for lm in location_guide["landmarks"]]
    assert "lm-albalad" in landmark_ids  # Al-Balad Historic District, Jeddah

    # 2. Guide details for the selected landmark (location + images enriched)
    resp = client.get("/api/v1/guide/landmarks/lm-albalad")
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    landmark_guide = resp.get_json()
    assert landmark_guide["landmark"]["id"] == "lm-albalad"
    assert landmark_guide["location"]["id"] == "loc-jeddah"

    # 3. Gemini Guide chat about the landmark. No GEMINI_API_KEY is configured
    # in the test environment, so this must fail cleanly (503, typed error) —
    # never a raw 500 or a leaked stack trace / key.
    resp = client.post(
        "/api/guide/chat",
        json={"landmark_id": "lm-albalad", "user_message": "Tell me about this place.", "language": "en"},
    )
    assert resp.status_code in (200, 503)
    _assert_no_secrets_or_forbidden_scope(app, resp)
    if resp.status_code == 503:
        assert resp.get_json()["error"]["code"] == "AI_SERVICE_UNAVAILABLE"

    # 4. TTS narration of the guide's answer — always available via the dev
    # fallback even with no provider configured.
    resp = client.post(
        "/api/tts", json={"text": "Welcome to Al-Balad Historic District.", "language": "en"}
    )
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    tts_body = resp.get_json()
    assert tts_body["audio_base64"]
    assert tts_body["mime_type"] == "audio/wav"

    # 5. Camera -> vision analysis of a photo taken at the landmark. Also
    # needs GEMINI_API_KEY, so also expected to fail cleanly without one.
    import io

    fake_png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    resp = client.post(
        "/api/vision/analyze",
        data={
            "image": (io.BytesIO(fake_png), "photo.png"),
            "language": "en",
            "landmark_id": "lm-albalad",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code in (200, 503)
    _assert_no_secrets_or_forbidden_scope(app, resp)
    if resp.status_code == 503:
        assert resp.get_json()["error"]["code"] == "AI_SERVICE_UNAVAILABLE"

    # 6. Historical database / "See the Past" for the same landmark.
    resp = client.get("/api/history/landmarks/lm-albalad")
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    history_body = resp.get_json()
    assert history_body["count"] >= 1
    historical_image_id = history_body["results"][0]["id"]

    # 7. Gamification: discovering the landmark itself awards XP.
    resp = client.post(
        "/api/gamification/discover",
        json={"user_id": "flow-visitor", "type": "landmark", "item_id": "lm-albalad"},
    )
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    discover_body = resp.get_json()
    assert discover_body["already_discovered"] is False
    assert discover_body["xp_awarded"] == 10

    # 8. Gamification: viewing a "See the Past" record also awards XP and
    # rolls up into the same visitor profile.
    resp = client.post(
        "/api/gamification/discover",
        json={"user_id": "flow-visitor", "type": "historical_image", "item_id": historical_image_id},
    )
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    discover_body_2 = resp.get_json()
    assert discover_body_2["xp_awarded"] == 15

    # 9. Final profile reflects both discoveries.
    resp = client.get("/api/gamification/profile/flow-visitor")
    assert resp.status_code == 200
    _assert_no_secrets_or_forbidden_scope(app, resp)
    profile = resp.get_json()
    assert profile["total_xp"] == 25
    assert profile["discovered_landmarks"]["count"] == 1
    assert profile["historical_images_viewed"]["count"] == 1


def test_no_itinerary_pricing_booking_transportation_endpoints_exist(app):
    """
    Static guard on the route table itself: none of these forbidden
    feature areas should ever get a blueprint registered.
    """
    all_rules = " ".join(str(rule) for rule in app.url_map.iter_rules()).lower()
    for word in ("itinerary", "pricing", "booking", "transportation", "hotel"):
        assert word not in all_rules
