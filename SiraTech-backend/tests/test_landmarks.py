def test_list_landmarks(client):
    resp = client.get("/api/v1/landmarks")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] > 0


def test_filter_landmarks_by_location(client):
    resp = client.get("/api/v1/landmarks?location_id=loc-alula")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] >= 1
    assert all(lm["location_id"] == "loc-alula" for lm in body["results"])


def test_filter_landmarks_by_unknown_location_returns_404(client):
    resp = client.get("/api/v1/landmarks?location_id=nope")
    assert resp.status_code == 404


def test_filter_landmarks_unesco_only(client):
    resp = client.get("/api/v1/landmarks?unesco=true")
    assert resp.status_code == 200
    body = resp.get_json()
    assert all(lm["unesco"] is True for lm in body["results"])


def test_filter_landmarks_invalid_unesco_value(client):
    resp = client.get("/api/v1/landmarks?unesco=maybe")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_get_landmark_by_id(client):
    resp = client.get("/api/v1/landmarks/lm-hegra")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name_en"] == "Hegra (Mada'in Salih)"


def test_get_landmark_not_found(client):
    resp = client.get("/api/v1/landmarks/nope")
    assert resp.status_code == 404
