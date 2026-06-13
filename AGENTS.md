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
│   │   ├── main.py       # 13 routers, CORS, exception handlers, lifespan
│   │   ├── api/          # 12 routers: cameras, scenes, ROIs, rules, alerts, work-orders, users, auth, dashboard, alert-workflow, detection-events, health
│   │   ├── alerts/       # AlertService, AlertEventBus, CriticalAlertHandler, AlertWebSocketManager
│   │   ├── detectors/    # BaseDetector ABC, DebrisDetector (YOLO), FireSmokeDetector, DetectorRegistry
│   │   ├── rules/        # ObstructionRuleEngine (duration/area/forbidden-zone), CooldownTracker
│   │   └── ...           # core (settings), models (10 ORM), auth (JWT), camera, db, roi, schemas, notifications
│   ├── tests/            # 244 tests
│   └── pyproject.toml
├── frontend/             # Vue 3 + TypeScript + Element Plus SPA
│   ├── src/
│   │   ├── views/        # 11 views (Login, Dashboard, CameraList/Detail, SceneList/Detail, AlertList, WorkOrderList, UserList, RuleConfig, DetectionEventList)
│   │   ├── components/   # RoiCanvas.vue, AlertDetailDrawer
│   │   ├── composables/  # useAlertEvents (WebSocket)
│   │   └── ...           # layouts, api, auth, utils, router
│   └── e2e/              # 17 Playwright e2e tests
├── workers/              # Asyncio inspection worker system
│   ├── scheduler.py      # InspectionScheduler — periodic capture with failure backoff
│   ├── executor.py       # InspectionExecutor + BatchExecutor — concurrent camera capture
│   ├── pipeline.py       # DetectionPipeline: capture→detect→persist→rule→alert
│   ├── context.py        # CameraDetectionContext, CameraContextCache (TTL)
│   ├── metrics.py        # WorkerMetricsCollector
│   ├── models.py         # InspectionResult, WorkerMetrics, WorkerStatus, ScheduledCamera
│   └── run.py            # Entry point
├── shared/               # Cross-cutting (coordinate_standard, asset_paths)
├── scripts/              # Deployment scripts (install/uninstall/start/stop/update/status)
├── deploy/               # Config template (mallsenseai.env.example)
└── [legacy .py files]    # main.py, web_server.py, camera_manager.py, etc.
```

## Entry points and commands

| Command | Description |
|---------|-------------|
| `python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5380` | FastAPI backend (dev) |
| `cd frontend && npm run dev` | Vue 3 dev server on port 5373, proxies `/api` → `:5380` |
| `cd frontend && npm run build` | Production build (vue-tsc + vite) |
| `python3 -m pytest backend/tests/ -v` | Run 244 backend tests |
| `cd frontend && npx playwright test` | Run 17 e2e tests |
| `python3 -m workers.run` | Start inspection scheduler (asyncio worker) |

**CI (GitHub Actions)**: On push/PR to `main` — backend pytest (Python 3.10) + frontend vue-tsc + vite build (Node 22) + Playwright e2e (Chromium)

## Dev environment
- **Ports**: backend 5380, frontend 5373 (no conflict with mysqlbot 8000/5173, mi 5280/5273)
- **Database**: PostgreSQL 16 + pgvector in shared `postgres16` container, `langchat:langchat@localhost:5432/mallsenseai`
- **Config**: `.env` file (see `.env.example`). `CORS_ORIGINS` must be JSON array: `["http://localhost:5373"]`
- **Python**: 3.10 at `/usr/bin/python3` (`python` not available)
- **Install**: `pip install -e backend/` for new platform deps; `pip install -r requirements.txt` for legacy deps only

## Key domain concepts
- **Coordinates**: All ROI coordinates in normalized [0.0, 1.0] space. Conversion helpers in `shared/coordinate_standard.py`.
- **Camera credentials**: `Camera.password_hash` stores **plaintext** (needed for HTTP/RTSP auth to cameras), not bcrypt. `User.password_hash` is properly bcrypt-hashed.
- **Detection pipeline**: `scheduler.py` → `executor.py` (capture) → detectors (YOLO debris/fire-smoke) → `pipeline._persist_detections()` (audit to `detection_events` table) → `rules/engine.py` → `alerts/service.py` → `notifications/service.py`
- **Alert lifecycle**: `pending` → `confirmed` → `resolved` (or `false_positive`). Work orders auto-created on confirm.
- **Real-time push**: WebSocket `/api/ws/alerts` (JWT auth). Frontend `useAlertEvents` composable + notification bell with unread badge and audio beep.
- **Auth**: JWT HS256 via python-jose. Token payload: `sub` (user ID) + `exp` only; frontend resolves user via `GET /api/users/{id}`.
- **Inspection worker**: Asyncio-based, per-camera intervals, exponential failure backoff (30s→60s→120s→300s), bounded concurrency (default 10), graceful SIGINT/SIGTERM.

## API surface (13 routers, ~55 endpoints)

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| auth | /api | POST /auth/login |
| cameras | /api | CRUD + POST /cameras/{id}/snapshot |
| scenes | /api | CRUD + PUT /scenes/{id}/baseline (upload) + GET baseline (download) |
| rois | /api | CRUD, filterable by scene_id |
| rules | /api | CRUD, filterable by camera_id |
| alerts | /api | GET list, GET/PUT by id |
| alert_workflow | /api | POST /alerts/{id}/confirm, /false-positive, /resolve; POST /work-orders/{id}/assign, /transition |
| work_orders | /api | CRUD + PATCH status, filterable by alert_id |
| users | /api | CRUD (admin bcrypt-hashed passwords) |
| dashboard | /api | GET /dashboard/stats |
| detection_events | /api | GET list (filterable by camera_id/roi_id/detected_at), GET by id |
| health | /api | GET /health |
| ws | /api | WebSocket /ws/alerts |

## Test coverage
- **Backend**: 244 — API (23), ROI engine (46), Rule engine (68), Pipeline+DetectionEvent (23), Workers (84)
- **Frontend e2e**: 17 Playwright tests — auth (2), navigation (2), cameras (1), scenes (1), alerts (1), alert-detail (3), detection-events (4), work-orders (1), users (1), dashboard (1)
- **CI**: 3 parallel jobs on every push/PR

## Known issues and gotchas
- LSP shows "could not be resolved" on all `backend.app.*` imports — workspace config issue, not real errors
- Root `requirements.txt` is for legacy system only; new platform uses `backend/pyproject.toml`
- CI backend job uses `pip install -r requirements.txt` (legacy deps) instead of `pip install -e backend/` — needs fixing
- Detection pipeline v1 uses in-memory event_bus per process — no cross-process messaging (same-process only)
- YOLO model files (.pt) excluded from Docker image — detectors gracefully degrade if weights missing
- Backend tests use SQLite; production uses PostgreSQL+pgvector — no integration test for pgvector features
- V2RAY proxy in tmux blocks uvicorn — must `unset http_proxy https_proxy` before starting dev server

## Dependency notes
- Backend: FastAPI, SQLAlchemy 2, Alembic, psycopg2-binary, pgvector, python-jose, passlib, httpx, shapely, ultralytics (YOLO)
- Frontend: Vue 3.5, Element Plus 2.9, Pinia 2.3, Vue Router 4.5, Axios, Playwright (dev)

## Git conventions
- Main branch: `main`, remote: `git@github.com:Gujiaweiguo/MallSenseAI.git`
- Commit messages follow conventional commits: `feat:`, `fix:`, `test:`, `ci:`, `chore:`, `docs:`
- No pre-commit hooks; CI validates on push

## 部署架构

| | 开发环境 | 生产环境 |
|---|---------|---------|
| 后端 | 本地 uvicorn | Docker 容器 |
| 前端 | Vite dev server | nginx 静态托管 |
| Worker | 本地 `python3 -m workers.run` | Docker 容器 |
| 数据库 | docker-compose.dev.yml (PG) | docker-compose.yml (PG, 持久卷) |
| 反向代理 | Vite proxy | nginx (`/api` → `backend:5380`) |

生产 4 服务: nginx:alpine + mallsenseai-app (backend+worker 共享镜像) + pgvector:pg16。仅 nginx 暴露端口，非 root 运行。

| 路径 | 用途 |
|------|------|
| `/opt/module/mallsenseai/` | 应用文件（代码、Dockerfile、compose） |
| `/opt/software/mallsenseai/mallsenseai.env` | 配置文件（自动生成随机密钥） |
| `/var/lib/mallsenseai/` | 持久数据（postgres、assets） |

部署脚本: `scripts/{install,uninstall,start,stop,update,status}.sh`

## Change 归档验证规则

### 1 人开发工作流
- 直接推 `main` 分支，CI 是唯一的自动 reviewer
- Conventional commits，OpenSpec archive 文件是功能完成的正式标记

### 测试分级标准

| 变更类型 | 单元测试 | 集成测试(API) | E2E 测试 |
|----------|---------|-------------|---------|
| 纯后端逻辑 | ✅ 必须 | 视影响范围 | — |
| 后端新端点 | ✅ 必须 | ✅ 必须 | — |
| 前端 UI 变更 | — | — | ✅ 必须 |
| 全栈变更 | ✅ 必须 | ✅ 必须 | ✅ 必须 |
| Workers/基础设施 | ✅ 必须 | 视影响范围 | — |

### 归档前验证清单

```
□ 1. 受影响模块有对应测试文件
□ 2. 新功能有新测试用例覆盖
□ 3. python3 -m pytest backend/tests/ -q — 全部通过
□ 4. cd frontend && npx vue-tsc --noEmit — 零错误
□ 5. cd frontend && npm run build — 构建成功
□ 6. 如有前端变更：cd frontend && npx playwright test — 全部通过
□ 7. 没有引入新的 type: any / @ts-ignore / bare except
```
