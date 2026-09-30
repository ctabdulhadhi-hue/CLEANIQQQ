import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from app.core.session_store import session_store

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CleanIQ API"
    assert data["version"] == "1.0.0"
    assert isinstance(data["active_sessions"], int)
    assert data["active_sessions"] >= 0


def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "CleanIQ API"
    assert data["version"] == "1.0.0"
    assert isinstance(data["active_sessions"], int)


def test_health_active_sessions_tracking():
    initial_res = client.get("/health").json()
    initial_count = initial_res["active_sessions"]

    test_id = "test_health_session_probe"
    session_store.set(test_id, pd.DataFrame({"col": [1, 2, 3]}))

    try:
        updated_res = client.get("/health").json()
        assert updated_res["active_sessions"] == initial_count + 1
    finally:
        session_store.delete(test_id)
        cleanup_res = client.get("/health").json()
        assert cleanup_res["active_sessions"] == initial_count


def test_spa_client_side_routing_fallback():
    """Verify that client-side SPA routes (e.g. /dashboard, /upload) fallback to serving index.html."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "<!doctype html>" in res.text.lower() or "<html" in res.text.lower()


def test_spa_path_traversal_attempts_blocked():
    """Verify that path traversal attempts outside frontend/dist cannot retrieve host files."""
    traversal_paths = [
        "/%2e%2e/%2e%2e/backend/app/main.py",
        "/%2e%2e/%2e%2e/backend/requirements.txt",
        "/%2e%2e/%2e%2e/render.yaml",
        "/%252e%252e/%252e%252e/backend/app/main.py",
        "/..%5c..%5cbackend/app/main.py",
        "/....//....//backend/app/main.py",
    ]
    for path in traversal_paths:
        res = client.get(path)
        # Must NOT return HTTP 200 with server file content
        assert res.status_code in (400, 404), f"Path {path} returned unexpected status {res.status_code}"
        assert "OPENBLAS_NUM_THREADS" not in res.text
        assert "uvicorn" not in res.text
        assert "buildCommand" not in res.text


def test_spa_null_byte_path_rejected():
    """Verify that paths containing null bytes are cleanly rejected."""
    res = client.get("/index.html%00test")
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "HTTP_400"


def test_spa_serves_valid_static_asset():
    """Verify that legitimate static assets within frontend/dist are served correctly."""
    res = client.get("/index.html")
    assert res.status_code == 200
    assert "<!doctype html>" in res.text.lower() or "<html" in res.text.lower()
