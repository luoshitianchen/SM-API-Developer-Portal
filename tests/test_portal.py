"""开发者门户业务域深化测试：应用 / 凭证 / 调用日志。"""
from __future__ import annotations

H = {"X-Internal-Token": "test-internal-key-12345"}


# ═══════════════════════════════════════════════════════════
# 开发者应用
# ═══════════════════════════════════════════════════════════

class TestDeveloperApps:
    async def test_create_app_success(self, client):
        resp = await client.post("/api/portal/apps", json={
            "name": "电商应用", "owner": "运营团队",
            "description": "面向 C 端的电商应用",
        }, headers=H)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "电商应用"
        assert data["status"] == "pending_review"
        assert data["app_id"].startswith("app_")

    async def test_list_apps_read_without_token(self, client):
        resp = await client.get("/api/portal/apps")
        assert resp.status_code == 200
        assert "total" in resp.json()

    async def test_create_app_requires_token(self, client):
        resp = await client.post("/api/portal/apps", json={"name": "无令牌应用"})
        assert resp.status_code == 403

    async def test_get_app_by_id(self, client):
        create = await client.post("/api/portal/apps", json={"name": "查询应用"}, headers=H)
        aid = create.json()["id"]
        resp = await client.get(f"/api/portal/apps/{aid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == aid

    async def test_get_app_not_found(self, client):
        resp = await client.get("/api/portal/apps/nonexistent")
        assert resp.status_code == 404

    async def test_approve_app(self, client):
        create = await client.post("/api/portal/apps", json={"name": "待审核应用"}, headers=H)
        aid = create.json()["id"]
        resp = await client.patch(f"/api/portal/apps/{aid}/status",
                                   json={"status": "active"}, headers=H)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_disabled_cannot_reactivate(self, client):
        create = await client.post("/api/portal/apps", json={"name": "禁用应用"}, headers=H)
        aid = create.json()["id"]
        await client.patch(f"/api/portal/apps/{aid}/status",
                           json={"status": "active"}, headers=H)
        await client.patch(f"/api/portal/apps/{aid}/status",
                           json={"status": "disabled"}, headers=H)
        resp = await client.patch(f"/api/portal/apps/{aid}/status",
                                   json={"status": "active"}, headers=H)
        assert resp.status_code == 400

    async def test_update_app(self, client):
        create = await client.post("/api/portal/apps", json={"name": "旧名称"}, headers=H)
        aid = create.json()["id"]
        resp = await client.patch(f"/api/portal/apps/{aid}",
                                   json={"name": "新名称", "owner": "新团队"}, headers=H)
        assert resp.status_code == 200
        assert resp.json()["name"] == "新名称"

    async def test_delete_app(self, client):
        create = await client.post("/api/portal/apps", json={"name": "删除应用"}, headers=H)
        aid = create.json()["id"]
        resp = await client.delete(f"/api/portal/apps/{aid}", headers=H)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 应用凭证
# ═══════════════════════════════════════════════════════════

class TestAppCredentials:
    async def _activate_app(self, client, name="凭证测试应用") -> str:
        create = await client.post("/api/portal/apps", json={"name": name}, headers=H)
        aid = create.json()["id"]
        await client.patch(f"/api/portal/apps/{aid}/status",
                           json={"status": "active"}, headers=H)
        return aid

    async def test_create_credential_success(self, client):
        aid = await self._activate_app(client)
        resp = await client.post(f"/api/portal/apps/{aid}/credentials",
                                  json={}, headers=H)
        assert resp.status_code == 201
        data = resp.json()
        assert "plain_client_secret" in data
        assert data["client_id"].startswith("cid_")
        assert data["status"] == "active"

    async def test_create_credential_inactive_app_rejected(self, client):
        create = await client.post("/api/portal/apps", json={"name": "未激活应用"}, headers=H)
        aid = create.json()["id"]
        resp = await client.post(f"/api/portal/apps/{aid}/credentials", json={}, headers=H)
        assert resp.status_code == 400

    async def test_list_credentials_read_without_token(self, client):
        aid = await self._activate_app(client, "凭证列表应用")
        await client.post(f"/api/portal/apps/{aid}/credentials", json={}, headers=H)
        resp = await client.get(f"/api/portal/apps/{aid}/credentials")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_revoke_credential(self, client):
        aid = await self._activate_app(client, "吊销应用")
        create = await client.post(f"/api/portal/apps/{aid}/credentials", json={}, headers=H)
        cid = create.json()["id"]
        resp = await client.patch(f"/api/portal/apps/credentials/{cid}/status",
                                   json={"status": "revoked"}, headers=H)
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

    async def test_revoked_credential_cannot_reactivate(self, client):
        aid = await self._activate_app(client, "不可恢复应用")
        create = await client.post(f"/api/portal/apps/{aid}/credentials", json={}, headers=H)
        cid = create.json()["id"]
        await client.patch(f"/api/portal/apps/credentials/{cid}/status",
                           json={"status": "revoked"}, headers=H)
        resp = await client.patch(f"/api/portal/apps/credentials/{cid}/status",
                                   json={"status": "active"}, headers=H)
        assert resp.status_code == 400

    async def test_delete_credential(self, client):
        aid = await self._activate_app(client, "删除凭证应用")
        create = await client.post(f"/api/portal/apps/{aid}/credentials", json={}, headers=H)
        cid = create.json()["id"]
        resp = await client.delete(f"/api/portal/apps/credentials/{cid}", headers=H)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════════════════
# 调用日志与统计
# ═══════════════════════════════════════════════════════════

class TestCallLogs:
    async def test_record_call_success(self, client):
        resp = await client.post("/api/portal/call-logs", json={
            "app_id": "app_demo1234", "api_path": "/api/v1/orders",
            "method": "GET", "status_code": 200, "latency_ms": 45,
        }, headers=H)
        assert resp.status_code == 201
        data = resp.json()
        assert data["api_path"] == "/api/v1/orders"
        assert data["latency_ms"] == 45

    async def test_record_call_requires_token(self, client):
        resp = await client.post("/api/portal/call-logs", json={
            "app_id": "app_notoken", "api_path": "/api/v1/x",
        })
        assert resp.status_code == 403

    async def test_list_logs_read_without_token(self, client):
        resp = await client.get("/api/portal/call-logs")
        assert resp.status_code == 200
        assert "total" in resp.json()

    async def test_list_logs_filter_by_status_code(self, client):
        await client.post("/api/portal/call-logs", json={
            "app_id": "app_filter", "api_path": "/a", "status_code": 500,
        }, headers=H)
        await client.post("/api/portal/call-logs", json={
            "app_id": "app_filter", "api_path": "/b", "status_code": 200,
        }, headers=H)
        resp = await client.get("/api/portal/call-logs?status_code=500&app_id=app_filter")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status_code"] == 500

    async def test_app_stats_aggregation(self, client):
        app_id = "app_stats_demo"
        await client.post("/api/portal/call-logs", json={
            "app_id": app_id, "api_path": "/x", "status_code": 200, "latency_ms": 10,
        }, headers=H)
        await client.post("/api/portal/call-logs", json={
            "app_id": app_id, "api_path": "/y", "status_code": 500, "latency_ms": 90,
        }, headers=H)
        resp = await client.get(f"/api/portal/call-logs/stats/{app_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 2
        assert data["error_calls"] == 1
        assert data["avg_latency_ms"] == 50.0

    async def test_list_logs_keyword_search(self, client):
        await client.post("/api/portal/call-logs", json={
            "app_id": "app_kw", "api_path": "/api/v1/searchable",
        }, headers=H)
        resp = await client.get("/api/portal/call-logs?keyword=searchable")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
