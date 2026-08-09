def test_list_images(client):
    resp = client.get("/api/v1/images")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] > 0


def test_filter_images_by_landmark(client):
    resp = client.get("/api/v1/images?landmark_id=lm-hegra")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] >= 1
    assert all(img["landmark_id"] == "lm-hegra" for img in body["results"])


def test_filter_images_unknown_landmark_returns_404(client):
    resp = client.get("/api/v1/images?landmark_id=nope")
    assert resp.status_code == 404


def test_get_image_by_id(client):
    resp = client.get("/api/v1/images/img-hegra-1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["landmark_id"] == "lm-hegra"


def test_get_image_not_found(client):
    resp = client.get("/api/v1/images/nope")
    assert resp.status_code == 404
