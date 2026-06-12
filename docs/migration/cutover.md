# MallSenseAI Migration and Cutover Plan

## Overview

This document describes the step-by-step procedure for migrating from the legacy Flask/Tkinter camera alarm system to the new FastAPI/Vue platform.

## Pre-Migration Checklist

- [ ] Verify `camera_configs.json` is present and up-to-date in project root
- [ ] Verify `alarm_images/` contains expected per-camera directories
- [ ] Verify PostgreSQL + pgvector is accessible (or SQLite for dev)
- [ ] Create database backup (if production)
- [ ] Verify `.env` is configured with correct `DATABASE_URL`
- [ ] Install new platform dependencies: `pip install -r backend/requirements.txt` or `uv sync`

## Migration Procedure

### Step 1: Run database migrations

```bash
# Create all platform tables
alembic -c backend/app/db/alembic.ini upgrade head
```

### Step 2: Dry-run migration

Always run dry-run first to preview what will happen:

```bash
python3 -m backend.app.db.run_migration --dry-run
```

Review the output for:
- Camera count matches expected (21 cameras)
- Duplicate location warnings for "4层西山4014铺旁通道"
- Degenerate ROI counts (expected ~17 degenerate out of 21)
- Missing baseline images
- Any conflicts or errors

### Step 3: Verify dry-run output

Check that:
- Cameras: ~21 inserts expected
- Scenes: ~21 inserts (one per camera)
- ROIs: ~2-4 real ROIs (the rest are degenerate and skipped)
- Rules: ~42 inserts (2 default rules per camera)
- Notifications: 1 insert (WeChat group + channel)

### Step 4: Real-run migration

```bash
python3 -m backend.app.db.run_migration --real-run
```

Verify exit code is 0 (or 2 if conflicts exist but are acceptable).

### Step 5: Verify migrated data

```bash
# Start the API
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Check camera count
curl -s http://localhost:8000/api/cameras | python3 -m json.tool | head -20
```

### Step 6: Isolate legacy code

```bash
bash scripts/isolate_legacy.sh
```

This copies legacy files to `legacy/` without deleting originals.

## Parallel Operation Period

During the parallel period, BOTH systems can run:

- **Legacy system**: `python3 main.py` — continues using `camera_configs.json` and `alarm_images/`
- **New platform**: `uvicorn backend.app.main:app` — uses the database
- **New workers**: `python3 -m workers.run` — starts inspection scheduler

Both systems share:
- `alarm_images/` (image assets)
- `yolov8*.pt` (model weights)

### Transition Rules During Parallel Period

1. Camera configuration changes should be made via the NEW platform API only
2. The legacy system should be treated as read-only for monitoring
3. New alert events from the new platform are authoritative
4. Legacy alert events are informational only

## Rollback Procedure

If the new platform has issues:

1. Stop the new platform: kill `uvicorn` and `workers` processes
2. Verify legacy system still works: `python3 main.py`
3. Legacy files in root are untouched — no data loss
4. Database data persists — no need to re-migrate

## Legacy Retirement Criteria

The legacy system can be retired when ALL of:

- [ ] All cameras are confirmed accessible via the new platform API
- [ ] Baseline images are migrated and viewable in the Vue console
- [ ] ROI zones are verified for cameras that had real polygon data
- [ ] At least one full inspection cycle completes successfully via new workers
- [ ] Alert generation and notification delivery confirmed working
- [ ] Operators trained on new Vue console

## Final Retirement Steps

1. Stop legacy `main.py` process
2. Move remaining legacy root files to `legacy/` (main.py, alarm_system.py, camera.py, etc.)
3. Update any deployment scripts to use new entry points only
4. Archive `legacy/` directory (do not delete — keep for reference)
5. Update `camera_configs.json` and `config.py` to read-only status markers

## Timeline Recommendation

| Phase | Duration | Description |
|---|---|---|
| Migration & verification | Day 1 | Run migration, verify data, fix any issues |
| Parallel operation | Days 2-7 | Both systems running, operators familiarizing |
| Legacy retirement | Day 7+ | Once criteria met, retire legacy system |
