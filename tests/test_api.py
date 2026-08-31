"""SM API Developer Portal 领域测试：API/应用/API Key/订阅/校验。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _api(client):
    return client.post("/api/portal/apis", json={"name": "orders", "path": "/v1/orders", "method": "GET"}).json()["id"]


def _app(client):
    return client.post("/api/portal/apps", json={"name": "billing-app", "owner": "财务部"}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_api_and_app_crud(client):
    assert client.post("/api/portal/apis", json={"name": "orders", "path": "/v1/orders"}).status_code == 201
    assert client.post("/api/portal/apis", json={"name": "orders", "path": "/v1/orders"}).status_code == 409
    assert client.post("/api/portal/apps", json={"name": "app1", "owner": "o"}).status_code == 201
    assert client.get("/api/portal/apis").json()["total"] == 1
    assert client.get("/api/portal/apps").json()["total"] == 1


def test_issue_and_validate_key(client):
    app_id = _app(client)
    issued = client.post(f"/api/portal/apps/{app_id}/keys").json()
    assert issued["api_key"].startswith("smk_")
    key_id = issued["id"]
    assert client.get(f"/api/portal/apps/{app_id}/keys").json()["total"] == 1
    valid = client.post("/api/portal/keys/validate", json={"api_key": issued["api_key"]}).json()
    assert valid["valid"] is True
    # 明文不落库：list 不含 api_key 字段
    listed = client.get(f"/api/portal/apps/{app_id}/keys").json()["items"][0]
    assert "api_key" not in listed
    # 吊销后校验失败
    client.post(f"/api/portal/keys/{key_id}/revoke")
    assert client.post("/api/portal/keys/validate", json={"api_key": issued["api_key"]}).status_code == 401


def test_subscription(client):
    api_id = _api(client)
    app_id = _app(client)
    sub = client.post("/api/portal/subscriptions", json={"app_id": app_id, "api_id": api_id, "quota_per_minute": 200})
    assert sub.status_code == 201
    assert client.post("/api/portal/subscriptions", json={"app_id": app_id, "api_id": api_id}).status_code == 409


def test_usage(client):
    api_id = _api(client)
    app_id = _app(client)
    client.post("/api/portal/subscriptions", json={"app_id": app_id, "api_id": api_id})
    usage = client.get("/api/portal/usage").json()
    assert usage["apis"] == 1
    assert usage["apps"] == 1
    assert usage["subscriptions"] == 1


def test_missing_entities(client):
    assert client.post("/api/portal/apps/nope/keys").status_code == 404
    assert client.post("/api/portal/subscriptions", json={"app_id": "no-such-app", "api_id": "no-such-api"}).status_code == 404


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/portal/apis", json={"name": "x", "path": "/x"}).status_code == 401
