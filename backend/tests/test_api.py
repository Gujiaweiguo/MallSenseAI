from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.models import Camera, DetectionEvent, DetectorType
from backend.tests.conftest import TestingSessionLocal

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_login_success(self, client: TestClient):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client: TestClient):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_protected_without_token(self, client: TestClient):
        resp = client.get("/api/cameras")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Camera CRUD
# ---------------------------------------------------------------------------

CAMERA_PAYLOAD = {
    "name": "Test Cam",
    "location": "Test Location",
    "ip": "192.168.1.100",
    "port": 80,
    "username": "admin",
    "password": "testpass",
}


class TestCameraCRUD:
    def test_create_camera(self, client: TestClient, auth_headers: dict):
        resp = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Cam"
        assert data["ip"] == "192.168.1.100"
        assert "password" not in data

    def test_list_cameras(self, client: TestClient, auth_headers: dict):
        client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers)
        resp = client.get("/api/cameras", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_camera(self, client: TestClient, auth_headers: dict):
        created = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        resp = client.get(f"/api/cameras/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_update_camera(self, client: TestClient, auth_headers: dict):
        created = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        resp = client.put(
            f"/api/cameras/{created['id']}",
            json={"name": "Updated Cam"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Cam"

    def test_delete_camera(self, client: TestClient, auth_headers: dict):
        created = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        resp = client.delete(f"/api/cameras/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204

    def test_get_camera_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/cameras/99999", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scene CRUD
# ---------------------------------------------------------------------------


class TestSceneCRUD:
    def test_create_scene(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        resp = client.post(
            "/api/scenes",
            json={"camera_id": cam["id"], "name": "Test Scene"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Test Scene"

    def test_list_scenes(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/scenes", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Alert / Rule / User
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_list_alerts_empty(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestRules:
    def test_create_and_list_rule(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        rule_payload = {
            "camera_id": cam["id"],
            "rule_type": "obstruction_area",
            "config": {"threshold": 0.3},
            "enabled": True,
            "priority": 100,
        }
        created = client.post("/api/rules", json=rule_payload, headers=auth_headers).json()
        assert created["rule_type"] == "obstruction_area"

        listed = client.get("/api/rules", headers=auth_headers).json()
        assert len(listed) >= 1


class TestUsers:
    def test_list_users(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/users", headers=auth_headers)
        assert resp.status_code == 200
        assert any(u["username"] == "admin" for u in resp.json())

    def test_create_user(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/users",
            json={
                "username": "operator1",
                "display_name": "Op One",
                "password": "pass123",
                "role": "operator",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "operator1"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_stats(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "cameras_total" in data
        assert "alerts_total" in data
        assert "work_orders_total" in data
        assert "alerts_by_severity" in data

    def test_health_no_auth(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Detection Events (read-only API)
# ---------------------------------------------------------------------------


class TestDetectionEvents:
    def test_list_empty(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/detection-events", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_events(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        db.add(
            DetectionEvent(
                camera_id=cam["id"],
                roi_id=None,
                detector_type=DetectorType.yolo,
                confidence=0.85,
                evidence_path=None,
                event_metadata={"label": "bottle"},
                detected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/detection-events", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["detector_type"] == "yolo"
        assert data[0]["confidence"] == 0.85

    def test_get_single_event(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        event = DetectionEvent(
            camera_id=cam["id"],
            roi_id=None,
            detector_type=DetectorType.yolo,
            confidence=0.9,
            evidence_path="/evidence.jpg",
            event_metadata={"label": "fire"},
            detected_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
        db.close()

        resp = client.get(f"/api/detection-events/{event_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == event_id
        assert resp.json()["confidence"] == 0.9

    def test_get_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/detection-events/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_filter_by_camera_id(self, client: TestClient, auth_headers: dict):
        cam1 = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        cam2_payload = {**CAMERA_PAYLOAD, "ip": "192.168.1.101", "name": "Cam 2"}
        cam2 = client.post("/api/cameras", json=cam2_payload, headers=auth_headers).json()
        db = TestingSessionLocal()
        db.add(
            DetectionEvent(
                camera_id=cam1["id"],
                roi_id=None,
                detector_type=DetectorType.yolo,
                confidence=0.8,
                event_metadata={},
                detected_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            DetectionEvent(
                camera_id=cam2["id"],
                roi_id=None,
                detector_type=DetectorType.yolo,
                confidence=0.7,
                event_metadata={},
                detected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        db.close()

        resp = client.get(f"/api/detection-events?camera_id={cam1['id']}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["camera_id"] == cam1["id"]

    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/detection-events")
        assert resp.status_code == 401
