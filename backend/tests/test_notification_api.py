from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.models import NotificationChannel
from backend.tests.conftest import TestingSessionLocal

GROUP_PAYLOAD = {
    "name": "Ops Team",
    "severities": ["high", "critical"],
    "enabled": True,
}

CHANNEL_PAYLOAD = {
    "channel_type": "wecom",
    "config": {"webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"},
    "enabled": True,
}


# ---------------------------------------------------------------------------
# Notification Group CRUD
# ---------------------------------------------------------------------------


class TestNotificationGroupCRUD:
    def test_create_group(self, client: TestClient, auth_headers: dict):
        resp = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Ops Team"
        assert data["channels"]["severities"] == ["high", "critical"]
        assert data["enabled"] is True
        assert data["notification_channels"] == []

    def test_list_groups(self, client: TestClient, auth_headers: dict):
        client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/notification-groups", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_group(self, client: TestClient, auth_headers: dict):
        created = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        resp = client.get(f"/api/notification-groups/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_group_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/notification-groups/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_update_group(self, client: TestClient, auth_headers: dict):
        created = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        resp = client.put(
            f"/api/notification-groups/{created['id']}",
            json={"name": "Updated Group", "severities": ["low", "medium"], "enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Group"
        assert data["channels"]["severities"] == ["low", "medium"]
        assert data["enabled"] is False

    def test_delete_group(self, client: TestClient, auth_headers: dict):
        created = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        resp = client.delete(f"/api/notification-groups/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204
        # Verify deletion
        resp2 = client.get(f"/api/notification-groups/{created['id']}", headers=auth_headers)
        assert resp2.status_code == 404

    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/notification-groups")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Notification Channel CRUD
# ---------------------------------------------------------------------------


class TestNotificationChannelCRUD:
    def test_create_channel(self, client: TestClient, auth_headers: dict):
        group = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        resp = client.post(
            f"/api/notification-groups/{group['id']}/channels",
            json=CHANNEL_PAYLOAD,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["channel_type"] == "wecom"
        assert data["group_id"] == group["id"]
        assert data["config"]["webhook_url"].startswith("https://")

    def test_update_channel(self, client: TestClient, auth_headers: dict):
        group = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        channel = client.post(
            f"/api/notification-groups/{group['id']}/channels",
            json=CHANNEL_PAYLOAD,
            headers=auth_headers,
        ).json()
        resp = client.put(
            f"/api/notification-groups/channels/{channel['id']}",
            json={"config": {"webhook_url": "https://new-url.com"}, "enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["config"]["webhook_url"] == "https://new-url.com"
        assert data["enabled"] is False

    def test_delete_channel(self, client: TestClient, auth_headers: dict):
        group = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        channel = client.post(
            f"/api/notification-groups/{group['id']}/channels",
            json=CHANNEL_PAYLOAD,
            headers=auth_headers,
        ).json()
        resp = client.delete(f"/api/notification-groups/channels/{channel['id']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_channel_appears_in_group(self, client: TestClient, auth_headers: dict):
        group = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        client.post(
            f"/api/notification-groups/{group['id']}/channels",
            json=CHANNEL_PAYLOAD,
            headers=auth_headers,
        )
        resp = client.get(f"/api/notification-groups/{group['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["notification_channels"]) == 1

    def test_delete_group_cascades_channels(self, client: TestClient, auth_headers: dict):
        group = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        channel = client.post(
            f"/api/notification-groups/{group['id']}/channels",
            json=CHANNEL_PAYLOAD,
            headers=auth_headers,
        ).json()
        assert channel["id"] is not None
        client.delete(f"/api/notification-groups/{group['id']}", headers=auth_headers)
        # Verify channel was cascade-deleted via DB
        db = TestingSessionLocal()
        leftover = db.get(NotificationChannel, channel["id"])
        db.close()
        assert leftover is None

    def test_create_channel_sms_type(self, client: TestClient, auth_headers: dict):
        group = client.post("/api/notification-groups", json=GROUP_PAYLOAD, headers=auth_headers).json()
        resp = client.post(
            f"/api/notification-groups/{group['id']}/channels",
            json={
                "channel_type": "sms",
                "config": {"provider": "stub", "phone_numbers": ["+15550001111"]},
                "enabled": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["channel_type"] == "sms"

    def test_update_channel_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.put(
            "/api/notification-groups/channels/99999",
            json={"enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_delete_channel_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.delete("/api/notification-groups/channels/99999", headers=auth_headers)
        assert resp.status_code == 404
