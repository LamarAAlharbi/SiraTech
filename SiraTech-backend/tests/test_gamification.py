def _badge_codes(body):
    return {b["code"] for b in body["badges"]}


def _new_badge_codes(body):
    return {b["code"] for b in body["newly_unlocked_badges"]}


def test_profile_for_new_user_is_all_zero(client):
    resp = client.get("/api/gamification/profile/u-new")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user_id"] == "u-new"
    assert body["total_xp"] == 0
    assert body["discovered_landmarks"] == {"count": 0, "item_ids": []}
    assert body["hidden_gems"] == {"count": 0, "item_ids": []}
    assert body["historical_images_viewed"] == {"count": 0, "item_ids": []}
    assert body["stories_listened"] == {"count": 0, "item_ids": []}
    assert body["badges"] == []


def test_discover_landmark_awards_xp_and_updates_profile(client):
    resp = client.post(
        "/api/gamification/discover",
        json={"user_id": "u1", "type": "landmark", "item_id": "lm-diriyah"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["already_discovered"] is False
    assert body["xp_awarded"] == 10
    assert body["newly_unlocked_badges"] == []
    assert body["profile"]["total_xp"] == 10
    assert body["profile"]["discovered_landmarks"]["count"] == 1
    assert "lm-diriyah" in body["profile"]["discovered_landmarks"]["item_ids"]


def test_discovering_same_landmark_twice_does_not_double_reward(client):
    first = client.post(
        "/api/gamification/discover",
        json={"user_id": "u1", "type": "landmark", "item_id": "lm-diriyah"},
    )
    assert first.get_json()["xp_awarded"] == 10

    second = client.post(
        "/api/gamification/discover",
        json={"user_id": "u1", "type": "landmark", "item_id": "lm-diriyah"},
    )
    body = second.get_json()
    assert second.status_code == 200
    assert body["already_discovered"] is True
    assert body["xp_awarded"] == 0
    assert body["newly_unlocked_badges"] == []
    # Total XP is unaffected by the repeat discovery.
    assert body["profile"]["total_xp"] == 10
    assert body["profile"]["discovered_landmarks"]["count"] == 1


def test_unknown_landmark_id_returns_404(client):
    resp = client.post(
        "/api/gamification/discover",
        json={"user_id": "u1", "type": "landmark", "item_id": "nope"},
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_invalid_discovery_type_returns_400(client):
    resp = client.post(
        "/api/gamification/discover",
        json={"user_id": "u1", "type": "not-a-real-type", "item_id": "lm-diriyah"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_required_fields_returns_400(client):
    resp = client.post("/api/gamification/discover", json={"type": "landmark"})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_heritage_explorer_and_saudi_heritage_explorer_badges_unlock(client):
    # Four landmarks in four distinct locations: this should cross both the
    # Heritage Explorer threshold (3 landmarks) and the Saudi Heritage
    # Explorer threshold (4 distinct locations) on the fourth discovery.
    landmark_ids = ["lm-diriyah", "lm-hegra", "lm-albalad", "lm-shubra-palace"]

    seen_badges = set()
    last_body = None
    for landmark_id in landmark_ids:
        resp = client.post(
            "/api/gamification/discover",
            json={"user_id": "u2", "type": "landmark", "item_id": landmark_id},
        )
        assert resp.status_code == 200
        last_body = resp.get_json()
        seen_badges |= _new_badge_codes(last_body)

    assert "heritage_explorer" in seen_badges
    assert "saudi_heritage_explorer" in seen_badges
    assert last_body["profile"]["total_xp"] == 40
    assert _badge_codes(last_body["profile"]) >= {"heritage_explorer", "saudi_heritage_explorer"}

    # Badges are never unlocked (or rewarded) twice.
    resp = client.post(
        "/api/gamification/discover",
        json={"user_id": "u2", "type": "landmark", "item_id": "lm-masmak"},
    )
    body = resp.get_json()
    assert "heritage_explorer" not in _new_badge_codes(body)
    assert "saudi_heritage_explorer" not in _new_badge_codes(body)


def test_hidden_gem_hunter_badge_unlocks_after_three_hidden_gems(client):
    for i in range(1, 4):
        resp = client.post(
            "/api/gamification/discover",
            json={"user_id": "u3", "type": "hidden_gem", "item_id": f"gem-{i}"},
        )
        body = resp.get_json()
        assert body["xp_awarded"] == 25

    assert "hidden_gem_hunter" in _new_badge_codes(body)
    assert body["profile"]["hidden_gems"]["count"] == 3


def test_time_traveler_badge_unlocks_after_three_historical_images(client):
    image_ids = ["hist-diriyah-1", "hist-diriyah-2", "hist-masmak-1"]
    body = None
    for image_id in image_ids:
        resp = client.post(
            "/api/gamification/discover",
            json={"user_id": "u4", "type": "historical_image", "item_id": image_id},
        )
        assert resp.status_code == 200
        body = resp.get_json()

    assert "time_traveler" in _new_badge_codes(body)
    assert body["profile"]["historical_images_viewed"]["count"] == 3


def test_story_listener_badge_unlocks_after_three_stories(client):
    body = None
    for i in range(1, 4):
        resp = client.post(
            "/api/gamification/discover",
            json={"user_id": "u5", "type": "story", "item_id": f"story-{i}"},
        )
        body = resp.get_json()

    assert "story_listener" in _new_badge_codes(body)
    assert body["profile"]["stories_listened"]["count"] == 3


def test_profiles_are_isolated_per_user(client):
    client.post(
        "/api/gamification/discover",
        json={"user_id": "u-alice", "type": "landmark", "item_id": "lm-diriyah"},
    )

    alice = client.get("/api/gamification/profile/u-alice").get_json()
    bob = client.get("/api/gamification/profile/u-bob").get_json()

    assert alice["total_xp"] == 10
    assert bob["total_xp"] == 0
