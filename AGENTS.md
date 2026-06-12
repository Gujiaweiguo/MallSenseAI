# AGENTS.md

## Repo identity
- MallSenseAI: corridor obstruction detection platform migrated from a legacy Python alarm system to a FastAPI + Vue 3 architecture.
- **New platform** (active development): `backend/` (FastAPI API), `frontend/` (Vue 3 SPA), `workers/` (asyncio inspection scheduler), `shared/` (cross-cutting utilities).
- **Legacy system** (preserved, not actively developed): `main.py`, `web_server.py`, `camera_manager.py`, `alarm_system.py`, and supporting `.py` files in repo root.

## Architecture overview

```
MallSenseAI/
├── backend/              # FastAPI backend (Python 3.10)
│   ├── app/
│   │   ├── main.py       # FastAPI app, 11 routers, CORS, exception handlers
│   │   ├── core/         # Settings (pydantic-settings, .env)
│   │   ├── models/       # 10 ORM models (SQLAlchemy 2 + pgvector)
│   │   ├── api/          # 11 API routers (cameras, scenes, ROIs, rules, alerts, work-orders, users, auth, dashboard, alert-workflow)
│   │   ├── auth/         # JWT HS256 + bcrypt auth
│   │   ├── camera/       # DahuaCameraAdapter (httpx digest auth), CaptureService (TTL cache), HealthCheckService
│   │   ├── db/           # SQLAlchemy sessions, Alembic migrations, legacy migration scripts
│   │   ├── alerts/       # AlertService (lifecycle), WorkOrderStateMachine, AlertEventBus (pub/sub), CriticalAlertHandler
│   │   ├── notifications/# NotificationService (retry + backoff), WeComNotifier, TwilioSMSNotifier
│   │   ├── detectors/    # BaseDetector ABC, DebrisDetector (YOLO), FireSmokeDetector, DetectorRegistry
│   │   ├── roi/          # ROIEngine (point-in-polygon, IoU, area), validation, legacy importer
│   │   ├── rules/        # ObstructionRuleEngine (duration/area/forbidden-zone), CooldownTracker
│   │   └── schemas/      # Pydantic request/response schemas for all entities
│   ├── tests/            # 131 tests (API: 17, ROI engine: 46, Rule engine: 68)
│   └── pyproject.toml    # Backend dependencies
├── frontend/             # Vue 3 + TypeScript + Element Plus SPA
│   ├── src/
│   │   ├── views/        # 10 views (Login, Dashboard, CameraList/Detail, SceneList/Detail, AlertList, WorkOrderList, UserList, RuleConfig)
│   │   ├── components/   # RoiCanvas.vue (polygon drawing)
│   │   ├── layouts/      # MainLayout.vue (sidebar + header)
│   │   ├── api/          # Axios client, typed resources, TypeScript interfaces
│   │   ├── auth/         # Pinia auth store, JWT parsing, localStorage session
│   │   ├── utils/        # Shared constants, tag type mappings
│   │   └── router/       # 10 routes with auth/admin guards
│   └── e2e/              # 10 Playwright e2e tests (route mocking, no backend needed)
├── workers/              # Asyncio inspection worker system
│   ├── scheduler.py      # InspectionScheduler — periodic capture with failure backoff
│   ├── executor.py       # InspectionExecutor + BatchExecutor — concurrent camera capture
│   ├── metrics.py        # WorkerMetricsCollector — aggregate + per-camera metrics
│   ├── models.py         # InspectionResult, WorkerMetrics, WorkerStatus, ScheduledCamera
│   └── run.py            # Entry point: `python -m workers.run`
├── shared/               # Cross-cutting Python modules (imported by backend + workers)
│   ├── coordinate_standard.py  # Point types, pixel↔normalized coordinate conversion
│   └── asset_paths.py          # Canonical path templates for baselines, evidence, ROI snapshots
├── legacy/               # Legacy isolation plan (README only, files not yet moved)
├── scripts/              # isolate_legacy.sh — idempotent legacy file copier
├── docs/migration/       # cutover.md — full migration & cutover procedure
├── openspec/             # 7 archived changes + main specs
├── data/assets/cameras/  # New platform asset storage
├── alarm_images/         # Legacy camera data (shared during migration)
├── .github/workflows/    # CI: backend pytest + frontend vue-tsc + vite build
├── docker-compose.dev.yml # Reference compose for shared PostgreSQL 16 + Redis 7
└── [legacy .py files]    # main.py, web_server.py, camera_manager.py, alarm_system.py, etc.
```

## Entry points and commands

### New platform
| Command | Description |
|---------|-------------|
| `python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5380` | FastAPI backend (dev) |
| `cd frontend && npm run dev` | Vue 3 dev server on port 5373, proxies `/api` → `:5380` |
| `cd frontend && npm run build` | Production build (vue-tsc + vite) |
| `python3 -m pytest backend/tests/ -v` | Run 131 backend tests |
| `cd frontend && npx playwright test` | Run 10 e2e tests (Chromium, route mocking) |
| `python3 -m workers.run` | Start inspection scheduler (asyncio worker) |
| `python3 -m backend.app.db.run_migration --dry-run` | Legacy migration dry-run |
| `python3 -m backend.app.db.run_migration` | Legacy migration execution |

### Legacy system (still runnable)
| Command | Description |
|---------|-------------|
| `python main.py` | Interactive CLI alarm loop |
| `python web_server.py` | Flask API on port 5000 |
| `python camera_manager.py` | Tkinter GUI for camera management |

### CI (GitHub Actions)
- On push/PR to `main`: backend pytest (Python 3.10) + frontend vue-tsc + vite build (Node 22)

## Dev environment
- **Ports**: backend 5380, frontend 5373 (no conflict with mysqlbot 8000/5173, mi 5280/5273)
- **Database**: PostgreSQL 16 + pgvector in shared `postgres16` container, `langchat:langchat@localhost:5432/mallsenseai`
- **Redis**: shared `redis-dev` container, `localhost:6379`
- **Config**: `.env` file (see `.env.example`). `CORS_ORIGINS` must be JSON array: `["http://localhost:5373"]`
- **Python**: 3.10 at `/usr/bin/python3` (`python` not available)
- **Install**: `pip install -e backend/` for new platform deps; `pip install -r requirements.txt` for legacy deps only

## Data models (10 ORM tables)
| Model | Table | Purpose |
|-------|-------|---------|
| Camera | cameras | IP, location, credentials, status |
| Scene | scenes | Per-camera baseline image context |
| ROI | rois | Polygon geometry (normalized coords), zone type |
| Rule | rules | Detection rule (type, thresholds, priority, enabled) |
| Alert | alerts | Detection event (severity, status, evidence path) |
| WorkOrder | work_orders | Human task linked to alert |
| User | users | Platform user (admin/operator/viewer) |
| NotificationGroup | notification_groups | Alert recipient group |
| NotificationChannel | notification_channels | WeCom webhook, SMS, etc. |
| DetectionEvent | detection_events | Raw detector output (confidence, metadata) |

## Key domain concepts
- **Coordinates**: All ROI coordinates in normalized [0.0, 1.0] space. Conversion helpers in `shared/coordinate_standard.py`.
- **Camera credentials**: `Camera.password_hash` stores **plaintext** (needed for HTTP/RTSP auth to cameras), not bcrypt. `User.password_hash` is properly bcrypt-hashed.
- **Detection pipeline**: `workers/scheduler.py` → `executor.py` (capture) → detectors (YOLO debris/fire-smoke) → `rules/engine.py` (obstruction evaluation) → `alerts/service.py` (lifecycle) → `notifications/service.py` (dispatch)
- **Alert lifecycle**: `new` → `confirmed` → `resolved` (or `false_positive`). Work orders auto-created on confirm.
- **Auth**: JWT HS256 via python-jose. Token payload has `sub` (user ID) + `exp` only; frontend resolves full user profile via `GET /api/users/{id}`.
- **Inspection worker**: Asyncio-based periodic scheduler with per-camera intervals, exponential failure backoff (30s→60s→120s→300s), bounded concurrency (default 10), and graceful SIGINT/SIGTERM shutdown.

## API surface (11 routers, ~50 endpoints)
| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| auth | /api | POST /auth/login |
| cameras | /api | CRUD + POST /cameras/{id}/snapshot |
| scenes | /api | CRUD + PUT /scenes/{id}/baseline (upload) + GET baseline (download) |
| rois | /api | CRUD, filterable by scene_id |
| rules | /api | CRUD, filterable by camera_id |
| alerts | /api | GET list, GET/PUT by id |
| alert_workflow | /api | POST /alerts/{id}/confirm, /false-positive, /resolve; POST /work-orders/{id}/assign, /transition |
| work_orders | /api | CRUD + PATCH status |
| users | /api | CRUD (admin bcrypt-hashed passwords) |
| dashboard | /api | GET /dashboard/stats (aggregate counts) |
| health | /api | GET /health (liveness) |

## Frontend auth flow
1. `POST /api/auth/login` → `{access_token, token_type}`
2. Frontend stores JWT in `localStorage['mallsenseai.auth.token']`
3. Axios interceptor adds `Authorization: Bearer <token>` to all `/api` requests
4. 401 responses clear localStorage and redirect to `/login?redirect=...`
5. Auth guard: unauthenticated → `/login`; non-admin → `/users` redirects to `/`

## Test coverage
- **Backend**: 131 tests — API (17, FastAPI TestClient + file-based SQLite), ROI engine (46, pure unit), Rule engine (68, pure unit)
- **Frontend e2e**: 10 Playwright tests using `page.route()` mocking (no real backend)
- **CI**: GitHub Actions runs both on every push/PR

## Known issues and gotchas
- LSP shows "could not be resolved" on all `backend.app.*` imports — workspace config issue, not real errors
- Root `requirements.txt` is for legacy system only; new platform uses `backend/pyproject.toml`
- `notifications/router.py` is implemented but NOT wired in `main.py` — needs a startup event
- `workers/` is implemented but NOT integrated with detection pipeline yet (capture only, no detector→rule→alert wiring)
- `legacy/` directory contains only `README.md`; `scripts/isolate_legacy.sh` has not been run
- Duplicate location: "4层西山4014铺旁通道" for IPs 10.25.4.125 and 10.25.4.128 (2 known conflicts in legacy data)
- 17 of 20 legacy `safe_zones.json` are degenerate (all zeros); only 3 real ROIs were migrated
- V2RAY proxy in tmux blocks uvicorn — must `unset http_proxy https_proxy` before starting dev server
- `camera_manager.py` still resizes to `1600x1200` while new platform uses normalized coords

## Dependency notes
- Backend: FastAPI, SQLAlchemy 2, Alembic, psycopg2-binary, pgvector, python-jose, passlib, httpx, shapely, ultralytics (YOLO)
- Frontend: Vue 3.5, Element Plus 2.9, Pinia 2.3, Vue Router 4.5, Axios, Playwright (dev)
- Dev services: PostgreSQL 16 (pgvector extension), Redis 7

## Git conventions
- Main branch: `main`, remote: `git@github.com:Gujiaweiguo/MallSenseAI.git`
- Commit messages follow conventional commits: `feat:`, `fix:`, `test:`, `ci:`, `chore:`, `docs:`
- No pre-commit hooks; CI validates on push

## Change 归档验证规则

### 1 人开发工作流

- 直接推 `main` 分支，不做 feature branch + PR review
- CI（GitHub Actions）是唯一的自动 reviewer — 推送后必须 CI 绿灯才算完成
- 使用 conventional commits 描述变更意图，commit message 即变更记录
- OpenSpec archive 文件是功能完成的正式标记

### 测试分级标准（按变更类型）

| 变更类型 | 单元测试 | 集成测试(API) | E2E 测试 | 示例 |
|----------|---------|-------------|---------|------|
| 纯后端逻辑 | ✅ 必须 | 视影响范围 | — | ROI 引擎、规则引擎、检测器 |
| 后端新端点 | ✅ 必须 | ✅ 必须 | — | 新增 API router、修改 CRUD |
| 前端 UI 变更 | — | — | ✅ 必须 | 新视图、组件修改、交互逻辑 |
| 全栈变更 | ✅ 必须 | ✅ 必须 | ✅ 必须 | 前后端都改的 alert/work-order 流程 |
| Workers/基础设施 | ✅ 必须 | 视影响范围 | — | scheduler、executor、metrics |
| 文档/配置 | — | — | — | AGENTS.md、.env、docker-compose |

### 归档前验证清单（必须全部 ✅）

```
□ 1. 受影响模块有对应测试文件（新增模块必须有新测试）
□ 2. 新功能有新测试用例覆盖（不只是修改旧测试）
□ 3. python3 -m pytest backend/tests/ -q — 全部通过，零失败
□ 4. cd frontend && npx vue-tsc --noEmit — 零 TypeScript 错误
□ 5. cd frontend && npm run build — 构建成功
□ 6. 如有前端变更：cd frontend && npx playwright test — 全部通过
□ 7. 没有引入新的 type: any / @ts-ignore / bare except / as any
```

### CI 当前覆盖

| Job | 检查内容 | 运行时机 |
|-----|---------|---------|
| backend | `pytest backend/tests/` | 每次 push/PR 到 main |
| frontend | `vue-tsc --noEmit` + `vite build` | 每次 push/PR 到 main |

### 当前测试覆盖盲区（已知）

- Workers（scheduler、executor、metrics）零测试 — 下个 change 应补齐
- 后端测试用 SQLite，生产用 PostgreSQL+pgvector — 无集成测试
- Playwright e2e 测试未加入 CI — 仅本地运行
