def test_list_locations(client):
    resp = client.get("/api/v1/locations")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] > 0
    assert any(loc["id"] == "loc-alula" for loc in body["results"])


def test_filter_locations_by_region(client):
    resp = client.get("/api/v1/locations?region=Makkah Region")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] >= 1
    assert all(loc["region"] == "Makkah Region" for loc in body["results"])


def test_get_location_by_id(client):
    resp = client.get("/api/v1/locations/loc-alula")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name_en"] == "AlUla"


def test_get_location_not_found(client):
    resp = client.get("/api/v1/locations/does-not-exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_list_regions(client):
    resp = client.get("/api/v1/locations/regions")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "Makkah Region" in body["results"]
