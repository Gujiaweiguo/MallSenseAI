#!/usr/bin/env bash
set -euo pipefail

DB_NAME="mallsenseai"
DB_USER="langchat"
CONTAINER="postgres16"

echo "==> Checking ${CONTAINER}..."
docker exec "${CONTAINER}" pg_isready -U "${DB_USER}" || {
  echo "ERROR: ${CONTAINER} is not running. Start it first: docker start ${CONTAINER}"
  exit 1
}

echo "==> Ensuring database ${DB_NAME} exists..."
docker exec "${CONTAINER}" psql -U "${DB_USER}" -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
  docker exec "${CONTAINER}" psql -U "${DB_USER}" -c "CREATE DATABASE ${DB_NAME};"

echo "==> Creating tables + seeding data..."
cd /opt/code/MallSenseAI
python3 << 'PYEOF'
import os
from backend.app.db.session import engine, SessionLocal
from backend.app.models import Base, User
from backend.app.models.entities import Camera, Scene, Rule, CameraStatus, RuleType
from backend.app.auth.password import hash_password

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

existing = db.query(User).filter_by(username="admin").first()
if existing is None:
    db.add(User(username="admin", password_hash=hash_password("admin123"),
                display_name="Admin", role="admin", enabled=True))

CAMERAS = [
    ("10.25.4.59","L4009B铺后通道"),("10.25.4.50","L4021A铺后通道"),("10.25.4.40","L4016铺后通道"),
    ("10.25.4.6","4层影城旁通道"),("10.25.4.76","4层东山4038铺旁4号消防梯"),("10.25.4.66","4层东山4035铺后通道"),
    ("10.25.4.7","4层西山4013后通道1号消防梯"),("10.25.4.125","4层西山4014铺旁通道"),("10.25.4.117","4层西山4021B铺外围"),
    ("10.25.4.60","4层东山4009B铺后通道2"),("10.25.4.83","4层东山4004B铺旁通道2"),("10.25.4.41","4层西山4018铺后通道"),
    ("10.25.4.47","4层西山4021A-H18H19货梯厅"),("10.25.4.27","4层西山4022铺旁"),("10.25.4.96","4层东山4001铺旁11号货梯厅"),
    ("10.25.4.128","4层西山4014铺旁通道"),("10.25.4.119","4层西山4021B铺内通道"),("10.25.4.111","4层东山4007铺旁通道"),
    ("10.25.4.129","4层西山4014铺旁通道3"),("10.25.4.97","4层西山4001铺旁通道3"),("10.25.4.65","4层东山4035铺后通道1"),
]

if db.query(Camera).count() == 0:
    for ip, loc in CAMERAS:
        cam = Camera(name=loc, location=loc, ip=ip, port=80,
                     username="admin", password_hash="admin123", status=CameraStatus.active)
        db.add(cam); db.flush()
        scene = Scene(camera_id=cam.id, name=f"{loc} default scene")
        db.add(scene); db.flush()
        db.add(Rule(camera_id=cam.id, roi_id=None, rule_type=RuleType.fire_smoke,
                    config={"confidence_threshold":0.5,"min_area_ratio":0.01,"cooldown_seconds":30},
                    priority=10, enabled=True))
    for scene in db.query(Scene).all():
        for p in [f"data/assets/cameras/{scene.camera_id}/baseline.jpg",
                  f"data/assets/cameras/{scene.camera_id-1}/baseline.jpg"]:
            if os.path.exists(p):
                scene.baseline_image_path = p
                break

db.commit()
c_count = db.query(Camera).count()
s_count = db.query(Scene).count()
u_count = db.query(User).count()
db.close()
print(f"==> Seeded: {u_count} users, {c_count} cameras, {s_count} scenes")
PYEOF

echo "==> Verifying login..."
TOKEN=$(curl -s http://localhost:5380/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token","FAIL"))')

if [ "$TOKEN" = "FAIL" ] || [ -z "$TOKEN" ]; then
  echo "ERROR: Login failed. Is the backend running on :5380?"
  exit 1
fi

echo "==> Done. Admin login OK."
