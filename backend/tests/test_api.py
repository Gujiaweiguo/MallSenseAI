from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.models import Alert, Camera, DetectionEvent, DetectorType
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
# ROI CRUD
# ---------------------------------------------------------------------------


class TestRoiCRUD:
    def _create_scene(self, client: TestClient, auth_headers: dict) -> dict:
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        return client.post(
            "/api/scenes", json={"camera_id": cam["id"], "name": "Test Scene"}, headers=auth_headers
        ).json()

    def _create_roi(self, client: TestClient, auth_headers: dict, scene_id: int) -> dict:
        payload = {
            "scene_id": scene_id,
            "name": "Test ROI",
            "zone_type": "polygon",
            "geometry": {"type": "polygon", "points": [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]},
        }
        return client.post("/api/rois", json=payload, headers=auth_headers).json()

    def test_create_and_list_rois(self, client: TestClient, auth_headers: dict):
        scene = self._create_scene(client, auth_headers)
        roi = self._create_roi(client, auth_headers, scene["id"])
        assert roi["name"] == "Test ROI"

        resp = client.get(f"/api/rois?scene_id={scene['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_update_roi_name(self, client: TestClient, auth_headers: dict):
        scene = self._create_scene(client, auth_headers)
        roi = self._create_roi(client, auth_headers, scene["id"])

        resp = client.put(f"/api/rois/{roi['id']}", json={"name": "Renamed ROI"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed ROI"

    def test_update_roi_geometry(self, client: TestClient, auth_headers: dict):
        scene = self._create_scene(client, auth_headers)
        roi = self._create_roi(client, auth_headers, scene["id"])

        new_geometry = {"type": "polygon", "points": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]}
        resp = client.put(f"/api/rois/{roi['id']}", json={"geometry": new_geometry}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["geometry"]["points"] == new_geometry["points"]

    def test_delete_roi(self, client: TestClient, auth_headers: dict):
        scene = self._create_scene(client, auth_headers)
        roi = self._create_roi(client, auth_headers, scene["id"])

        resp = client.delete(f"/api/rois/{roi['id']}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/api/rois/{roi['id']}", headers=auth_headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Alert / Rule / User
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_list_alerts_empty(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_export_csv(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        db.add(Alert(
            camera_id=cam["id"],
            roi_id=None,
            rule_id=None,
            alert_type="obstruction_area",
            severity="high",
            status="pending",
            evidence_image_path=None,
            detected_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            resolved_at=None,
            event_metadata={},
        ))
        db.commit()
        db.close()

        resp = client.get("/api/alerts/export", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        lines = resp.text.strip().splitlines()
        assert lines[0] == "id,camera_id,alert_type,severity,status,detected_at,resolved_at"
        assert "obstruction_area" in lines[1]
        assert "high" in lines[1]
        assert "pending" in lines[1]

    def test_export_csv_with_severity_filter(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        db.add(Alert(
            camera_id=cam["id"], roi_id=None, rule_id=None, alert_type="obstruction_area",
            severity="high", status="pending", evidence_image_path=None,
            detected_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, event_metadata={},
        ))
        db.add(Alert(
            camera_id=cam["id"], roi_id=None, rule_id=None, alert_type="obstruction_area",
            severity="low", status="pending", evidence_image_path=None,
            detected_at=datetime(2026, 6, 1, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, event_metadata={},
        ))
        db.commit()
        db.close()

        resp = client.get("/api/alerts/export?severity=high", headers=auth_headers)
        assert resp.status_code == 200
        lines = resp.text.strip().splitlines()
        assert len(lines) == 2
        assert "high" in lines[1]

    def test_export_requires_auth(self, client: TestClient):
        resp = client.get("/api/alerts/export")
        assert resp.status_code == 401


class TestBatchAlerts:
    def _create_alerts(self, db, camera_id, count, status="pending"):
        for _ in range(count):
            db.add(Alert(
                camera_id=camera_id,
                roi_id=None,
                rule_id=None,
                alert_type="obstruction_area",
                severity="high",
                status=status,
                evidence_image_path=None,
                detected_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
                resolved_at=None,
                event_metadata={},
            ))
        db.commit()

    def test_batch_confirm(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        self._create_alerts(db, cam["id"], 3)
        alerts = db.query(Alert).filter(Alert.camera_id == cam["id"]).all()
        ids = [a.id for a in alerts]
        db.close()

        resp = client.post("/api/alerts/batch", json={"alert_ids": ids, "action": "confirm"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 3
        assert data["failed"] == []

    def test_batch_resolve(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        self._create_alerts(db, cam["id"], 2, status="confirmed")
        alerts = db.query(Alert).filter(Alert.camera_id == cam["id"]).all()
        ids = [a.id for a in alerts]
        db.close()

        resp = client.post("/api/alerts/batch", json={"alert_ids": ids, "action": "resolve"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 2
        assert data["failed"] == []

    def test_batch_mixed_states(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        # 1 pending (confirmable), 1 resolved (not confirmable)
        db.add(Alert(
            camera_id=cam["id"], roi_id=None, rule_id=None, alert_type="obstruction_area",
            severity="high", status="pending", evidence_image_path=None,
            detected_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, event_metadata={},
        ))
        db.add(Alert(
            camera_id=cam["id"], roi_id=None, rule_id=None, alert_type="obstruction_area",
            severity="high", status="resolved", evidence_image_path=None,
            detected_at=datetime(2026, 6, 1, 11, 0, 0, tzinfo=timezone.utc),
            resolved_at=None, event_metadata={},
        ))
        db.commit()
        alerts = db.query(Alert).filter(Alert.camera_id == cam["id"]).order_by(Alert.id).all()
        ids = [a.id for a in alerts]
        db.close()

        resp = client.post("/api/alerts/batch", json={"alert_ids": ids, "action": "confirm"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 1
        assert len(data["failed"]) == 1

    def test_batch_invalid_action(self, client: TestClient, auth_headers: dict):
        resp = client.post("/api/alerts/batch", json={"alert_ids": [1], "action": "delete"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_batch_requires_auth(self, client: TestClient):
        resp = client.post("/api/alerts/batch", json={"alert_ids": [1], "action": "confirm"})
        assert resp.status_code == 401


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
        assert resp.json()["database"] == "connected"


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

    def test_export_csv(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        db.add(
            DetectionEvent(
                camera_id=cam["id"],
                roi_id=None,
                detector_type=DetectorType.yolo,
                confidence=0.92,
                evidence_path=None,
                event_metadata={},
                detected_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        db.close()

        resp = client.get("/api/detection-events/export", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        lines = resp.text.strip().splitlines()
        assert lines[0] == "id,camera_id,roi_id,detector_type,confidence,detected_at"
        assert "yolo" in lines[1]

    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/detection-events")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Alert Evidence Image
# ---------------------------------------------------------------------------


class TestAlertEvidence:
    def test_evidence_not_found_no_path(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        alert = Alert(
            camera_id=cam["id"],
            roi_id=None,
            rule_id=None,
            alert_type="obstruction_area",
            severity="high",
            status="pending",
            evidence_image_path=None,
            detected_at=datetime.now(timezone.utc),
            resolved_at=None,
            event_metadata={},
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        alert_id = alert.id
        db.close()

        resp = client.get(f"/api/alerts/{alert_id}/evidence", headers=auth_headers)
        assert resp.status_code == 404

    def test_evidence_serves_file(self, client: TestClient, auth_headers: dict, tmp_path):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        evidence_file = tmp_path / "test_evidence.jpg"
        evidence_file.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-data")

        db = TestingSessionLocal()
        alert = Alert(
            camera_id=cam["id"],
            roi_id=None,
            rule_id=None,
            alert_type="obstruction_area",
            severity="high",
            status="pending",
            evidence_image_path=str(evidence_file),
            detected_at=datetime.now(timezone.utc),
            resolved_at=None,
            event_metadata={},
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        alert_id = alert.id
        db.close()

        resp = client.get(f"/api/alerts/{alert_id}/evidence", headers=auth_headers)
        assert resp.status_code == 200
        assert "image" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Dashboard Trend
# ---------------------------------------------------------------------------


class TestDashboardTrend:
    def test_trend_empty(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/dashboard/alert-trend", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_trend_returns_daily_counts(self, client: TestClient, auth_headers: dict):
        cam = client.post("/api/cameras", json=CAMERA_PAYLOAD, headers=auth_headers).json()
        db = TestingSessionLocal()
        now = datetime.now(timezone.utc)
        for i in range(3):
            db.add(Alert(
                camera_id=cam["id"],
                roi_id=None,
                rule_id=None,
                alert_type="obstruction_area",
                severity="high",
                status="pending",
                evidence_image_path=None,
                detected_at=now,
                resolved_at=None,
                event_metadata={},
            ))
        db.commit()
        db.close()

        resp = client.get("/api/dashboard/alert-trend?days=7", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        today_entry = data[-1]
        assert today_entry["count"] >= 3
