"""
Tests for GET /api/history/landmarks/<landmark_id> and
GET /api/history/images/<image_id> (See the Past).

All records currently served come from the sample placeholder dataset in
app/data/historical_images.json — these tests also guard the product rule
that sample data is always clearly labeled and never carries an invented
source URL or authenticity claim.
"""

from unittest.mock import patch


def test_history_for_landmark_returns_sample_records(client):
    resp = client.get("/api/history/landmarks/lm-diriyah")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["landmark_id"] == "lm-diriyah"
    assert body["count"] >= 1
    assert body["sample_data"] == "all"
    assert "placeholder data" in body["sample_data_notice"]
    assert all(r["landmark_id"] == "lm-diriyah" for r in body["results"])


def test_history_records_never_claim_authenticity_or_invent_sources(client):
    resp = client.get("/api/history/landmarks/lm-albalad")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] >= 1
    for record in body["results"]:
        assert record["is_sample"] is True
        # No fabricated archival URL — either omitted, or the frontend has
        # nothing pretending to be a verified citation.
        assert record["source_url"] is None
        assert "sample" in record["source"].lower()
        assert record["rights"]["license"] == "Unknown"


def test_history_for_landmark_has_expected_fields(client):
    resp = client.get("/api/history/landmarks/lm-hegra")
    body = resp.get_json()
    record = body["results"][0]
    for field in (
        "id",
        "landmark_id",
        "title",
        "image_path",
        "image_url",
        "year_or_period",
        "source",
        "source_url",
        "description",
        "tags",
        "rights",
        "is_sample",
    ):
        assert field in record


def test_history_for_landmark_filters_by_tag(client):
    resp = client.get("/api/history/landmarks/lm-albalad?tag=fashion")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] >= 1
    assert all("fashion" in r["tags"] for r in body["results"])


def test_history_for_landmark_invalid_tag_returns_400(client):
    resp = client.get("/api/history/landmarks/lm-albalad?tag=not-a-real-tag")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_history_for_unknown_landmark_returns_404(client):
    resp = client.get("/api/history/landmarks/nope")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_history_for_landmark_with_no_records_returns_empty_list(client):
    # lm-qatif-oasis has no seeded historical-image records yet.
    resp = client.get("/api/history/landmarks/lm-qatif-oasis")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 0
    assert body["results"] == []
    assert body["sample_data"] == "none"
    assert body["sample_data_notice"] is None


def test_get_history_image_by_id(client):
    resp = client.get("/api/history/images/hist-hegra-1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == "hist-hegra-1"
    assert body["landmark_id"] == "lm-hegra"
    assert body["is_sample"] is True
    assert body["source_url"] is None
    assert "not a real historical photograph" in body["sample_data_notice"]


def test_get_history_image_not_found_returns_404(client):
    resp = client.get("/api/history/images/nope")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


@patch("app.services.history_service.get_history_images_for_landmark")
def test_history_for_landmark_reports_mixed_sample_data(mock_get, client):
    # Simulates a landmark with one verified record alongside a sample one,
    # without inventing a real historical source in the actual dataset.
    mock_get.return_value = [
        {"id": "hist-fake-1", "landmark_id": "lm-hegra", "is_sample": True},
        {"id": "hist-fake-2", "landmark_id": "lm-hegra", "is_sample": False},
    ]

    resp = client.get("/api/history/landmarks/lm-hegra")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sample_data"] == "some"
    assert "Some of these records" in body["sample_data_notice"]


@patch("app.services.history_service.get_history_images_for_landmark")
def test_history_for_landmark_reports_no_sample_data(mock_get, client):
    mock_get.return_value = [
        {"id": "hist-fake-3", "landmark_id": "lm-hegra", "is_sample": False},
    ]

    resp = client.get("/api/history/landmarks/lm-hegra")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sample_data"] == "none"
    assert body["sample_data_notice"] is None
