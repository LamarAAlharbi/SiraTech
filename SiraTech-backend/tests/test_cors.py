"""
Verifies the CORS setup in app/__init__.py: /health is open to any origin,
while /api/* is restricted to the configured CORS_ORIGINS allowlist.
"""


def test_health_allows_any_origin(client):
    resp = client.get("/health", headers={"Origin": "http://some-other-app.example"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"


def test_api_allows_configured_origin(client):
    resp = client.get("/api/v1/locations", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_api_rejects_unconfigured_origin(client):
    resp = client.get("/api/v1/locations", headers={"Origin": "http://not-allowed.example"})
    assert resp.status_code == 200  # the request still succeeds server-side...
    # ...but no CORS header is sent back, so the browser blocks the frontend from reading it.
    assert resp.headers.get("Access-Control-Allow-Origin") is None
