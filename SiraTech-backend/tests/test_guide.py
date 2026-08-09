def test_search_requires_query(client):
    resp = client.get("/api/v1/guide/search")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_search_finds_landmark_by_name(client):
    resp = client.get("/api/v1/guide/search?q=Hegra")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total_results"] >= 1
    assert any(lm["id"] == "lm-hegra" for lm in body["landmarks"])


def test_search_finds_location_by_region(client):
    resp = client.get("/api/v1/guide/search?q=Makkah")
    assert resp.status_code == 200
    body = resp.get_json()
    assert any(loc["id"] == "loc-jeddah" for loc in body["locations"])


def test_landmark_guide_combines_data(client):
    resp = client.get("/api/v1/guide/landmarks/lm-hegra")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["landmark"]["id"] == "lm-hegra"
    assert body["location"]["id"] == "loc-alula"
    assert len(body["images"]) >= 1


def test_landmark_guide_not_found(client):
    resp = client.get("/api/v1/guide/landmarks/nope")
    assert resp.status_code == 404


def test_location_guide_combines_landmarks(client):
    resp = client.get("/api/v1/guide/locations/loc-alula")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["location"]["id"] == "loc-alula"
    assert len(body["landmarks"]) >= 1
