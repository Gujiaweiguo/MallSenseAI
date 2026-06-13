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
│   │   ├── main.py       # FastAPI app, 13 routers, CORS, exception handlers, lifespan
│   │   ├── core/         # Settings (pydantic-settings, .env)
│   │   ├── models/       # 10 ORM models (SQLAlchemy 2 + pgvector)
│   │   ├── api/          # 12 API routers (cameras, scenes, ROIs, rules, alerts, work-orders, users, auth, dashboard, alert-workflow, detection-events, health)
│   │   ├── auth/         # JWT HS256 + bcrypt auth
│   │   ├── camera/       # DahuaCameraAdapter (httpx digest auth), CaptureService (TTL cache), HealthCheckService
│   │   ├── db/           # SQLAlchemy sessions, Alembic migrations, legacy migration scripts
│   │   ├── alerts/       # AlertService (lifecycle), WorkOrderStateMachine, AlertEventBus (pub/sub), CriticalAlertHandler, AlertWebSocketManager
│   │   ├── notifications/# NotificationService (retry + backoff), WeComNotifier, TwilioSMSNotifier
│   │   ├── detectors/    # BaseDetector ABC, DebrisDetector (YOLO), FireSmokeDetector, DetectorRegistry
│   │   ├── roi/          # ROIEngine (point-in-polygon, IoU, area), validation, legacy importer
│   │   ├── rules/        # ObstructionRuleEngine (duration/area/forbidden-zone), CooldownTracker
│   │   └── schemas/      # Pydantic request/response schemas for all entities
│   ├── tests/            # 244 tests (API: 23, ROI engine: 46, Rule engine: 68, Pipeline: 9+14, Workers: 84)
│   └── pyproject.toml    # Backend dependencies
├── frontend/             # Vue 3 + TypeScript + Element Plus SPA
│   ├── src/
│   │   ├── views/        # 11 views (Login, Dashboard, CameraList/Detail, SceneList/Detail, AlertList, WorkOrderList, UserList, RuleConfig, DetectionEventList)
│   │   ├── components/   # RoiCanvas.vue (polygon drawing), AlertDetailDrawer (alert evidence + metadata + work orders)
│   │   ├── composables/  # useAlertEvents (WebSocket real-time alert push)
│   │   ├── layouts/      # MainLayout.vue (sidebar + header + notification bell)
│   │   ├── api/          # Axios client, typed resources, TypeScript interfaces
│   │   ├── auth/         # Pinia auth store, JWT parsing, localStorage session
│   │   ├── utils/        # Shared constants, tag type mappings (centralized)
│   │   └── router/       # 11 routes with auth/admin guards
│   └── e2e/              # 17 Playwright e2e tests (route mocking, no backend needed)
├── workers/              # Asyncio inspection worker system
│   ├── scheduler.py      # InspectionScheduler — periodic capture with failure backoff
│   ├── executor.py       # InspectionExecutor + BatchExecutor — concurrent camera capture
│   ├── metrics.py        # WorkerMetricsCollector — aggregate + per-camera metrics
│   ├── models.py         # InspectionResult, WorkerMetrics, WorkerStatus, ScheduledCamera
│   ├── context.py        # CameraDetectionContext, CameraContextCache (TTL), load_camera_context
│   ├── pipeline.py       # DetectionPipeline: capture→detect→persist→rule→alert orchestration
│   └── run.py            # Entry point: `python -m workers.run`
├── shared/               # Cross-cutting Python modules (imported by backend + workers)
│   ├── coordinate_standard.py  # Point types, pixel↔normalized coordinate conversion
│   └── asset_paths.py          # Canonical path templates for baselines, evidence, ROI snapshots
├── legacy/               # Legacy isolation plan (README only, files not yet moved)
├── scripts/              # Deployment scripts (install/uninstall/start/stop/update/status)
├── deploy/               # Deployment config template (mallsenseai.env.example)
├── docs/migration/       # cutover.md — full migration & cutover procedure
├── openspec/             # 7 archived changes + main specs
├── data/assets/cameras/  # New platform asset storage
├── alarm_images/         # Legacy camera data (shared during migration)
├── .github/workflows/    # CI: backend pytest + frontend vue-tsc + vite build + playwright e2e
├── docker-compose.dev.yml # Dev infrastructure — PostgreSQL 16 + pgvector only
└── [legacy .py files]    # main.py, web_server.py, camera_manager.py, alarm_system.py, etc.
```

## Entry points and commands

### New platform
| Command | Description |
|---------|-------------|
| `python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5380` | FastAPI backend (dev) |
| `cd frontend && npm run dev` | Vue 3 dev server on port 5373, proxies `/api` → `:5380` |
| `cd frontend && npm run build` | Production build (vue-tsc + vite) |
| `python3 -m pytest backend/tests/ -v` | Run 244 backend tests |
| `cd frontend && npx playwright test` | Run 17 e2e tests (Chromium, route mocking) || `python3 -m workers.run` | Start inspection scheduler (asyncio worker) |
| `python3 -m backend.app.db.run_migration --dry-run` | Legacy migration dry-run |
| `python3 -m backend.app.db.run_migration` | Legacy migration execution |

### Legacy system (still runnable)
| Command | Description |
|---------|-------------|
| `python main.py` | Interactive CLI alarm loop |
| `python web_server.py` | Flask API on port 5000 |
| `python camera_manager.py` | Tkinter GUI for camera management |

### CI (GitHub Actions)
- On push/PR to `main`: backend pytest (Python 3.10) + frontend vue-tsc + vite build (Node 22) + Playwright e2e (Chromium)

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
- **Detection audit**: All raw detections persisted to `detection_events` table via `pipeline._persist_detections()`, with ROI matching via centroid-in-polygon
- **Alert lifecycle**: `pending` → `confirmed` → `resolved` (or `false_positive`). Work orders auto-created on confirm.
- **Real-time push**: WebSocket endpoint `/api/ws/alerts` with JWT auth. Frontend receives alert events via `useAlertEvents` composable, notification bell with unread badge and audio beep.
- **Auth**: JWT HS256 via python-jose. Token payload has `sub` (user ID) + `exp` only; frontend resolves full user profile via `GET /api/users/{id}`.
- **Inspection worker**: Asyncio-based periodic scheduler with per-camera intervals, exponential failure backoff (30s→60s→120s→300s), bounded concurrency (default 10), and graceful SIGINT/SIGTERM shutdown.

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
| dashboard | /api | GET /dashboard/stats (aggregate counts) |
| detection_events | /api | GET list (filterable by camera_id/roi_id/detected_at range), GET by id |
| health | /api | GET /health (liveness) |
| ws | /api | WebSocket /ws/alerts (JWT auth, real-time alert push) |

## Frontend auth flow
1. `POST /api/auth/login` → `{access_token, token_type}`
2. Frontend stores JWT in `localStorage['mallsenseai.auth.token']`
3. Axios interceptor adds `Authorization: Bearer <token>` to all `/api` requests
4. 401 responses clear localStorage and redirect to `/login?redirect=...`
5. Auth guard: unauthenticated → `/login`; non-admin → `/users` redirects to `/`

## Test coverage
- **Backend**: 244 tests — API (23, FastAPI TestClient + file-based SQLite), ROI engine (46, pure unit), Rule engine (68, pure unit), Pipeline + DetectionEvent (23, mock-based), Workers (84: models 17, metrics 18, executor 10, scheduler 39)
- **Frontend e2e**: 17 Playwright tests — auth (2), navigation (2), cameras (1), scenes (1), alerts (1), alert-detail drawer (3), detection-events (4), work-orders (1), users (1), dashboard (1). Uses `page.route()` mocking, no real backend needed.
- **CI**: GitHub Actions runs all three on every push/PR

## Known issues and gotchas
- LSP shows "could not be resolved" on all `backend.app.*` imports — workspace config issue, not real errors
- Root `requirements.txt` is for legacy system only; new platform uses `backend/pyproject.toml`
- CI backend job uses `pip install -r requirements.txt` (legacy deps) instead of `pip install -e backend/` — needs fixing
- `legacy/` directory contains only `README.md`; `scripts/isolate_legacy.sh` has not been run
- Duplicate location: "4层西山4014铺旁通道" for IPs 10.25.4.125 and 10.25.4.128 (2 known conflicts in legacy data)
- 17 of 20 legacy `safe_zones.json` are degenerate (all zeros); only 3 real ROIs were migrated
- V2RAY proxy in tmux blocks uvicorn — must `unset http_proxy https_proxy` before starting dev server
- Detection pipeline v1 uses in-memory event_bus per process — no cross-process messaging (same-process only)
- YOLO model files (.pt) excluded from Docker image — detectors gracefully degrade if weights missing
- Backend tests use SQLite; production uses PostgreSQL+pgvector — no integration test for pgvector features

## Dependency notes
- Backend: FastAPI, SQLAlchemy 2, Alembic, psycopg2-binary, pgvector, python-jose, passlib, httpx, shapely, ultralytics (YOLO)
- Frontend: Vue 3.5, Element Plus 2.9, Pinia 2.3, Vue Router 4.5, Axios, Playwright (dev)
- Dev services: PostgreSQL 16 (pgvector extension), Redis 7

## Git conventions
- Main branch: `main`, remote: `git@github.com:Gujiaweiguo/MallSenseAI.git`
- Commit messages follow conventional commits: `feat:`, `fix:`, `test:`, `ci:`, `chore:`, `docs:`
- No pre-commit hooks; CI validates on push

## 部署架构

### 环境区分

| | 开发环境 | 生产环境 |
|---|---------|---------|
| 后端 | 本地 uvicorn (`python3 -m uvicorn`) | Docker 容器 |
| 前端 | Vite dev server (`npm run dev`) | nginx 静态托管 |
| Worker | 本地 `python3 -m workers.run` | Docker 容器 |
| 数据库 | docker-compose.dev.yml (PG 容器) | docker-compose.yml (PG 容器，持久卷) |
| 反向代理 | Vite proxy (`/api` → `:5380`) | nginx (`/api` → `backend:5380`) |

### 生产 Docker 架构（4 服务）

```
nginx:alpine ─── :80 → /usr/share/nginx/html (Vue SPA)
                     → /api/* proxy_pass → backend:5380
                     → /docs, /redoc proxy_pass → backend:5380

mallsenseai-app ─── backend: uvicorn on :5380
                  └── worker: python -m workers.run

pgvector/pgvector:pg16 ─── postgres:5432 (内部网络)
```

- 单一 Dockerfile，backend 和 worker 共享镜像，不同 `command`
- 所有服务在 `internal` Docker 网络中，仅 nginx 暴露端口
- 非 root 用户运行（appuser, uid 999）

### 目录布局

| 路径 | 用途 | 所有者 |
|------|------|--------|
| `/opt/module/mallsenseai/` | 应用文件（代码、Dockerfile、compose） | root |
| `/opt/software/mallsenseai/` | 配置文件 (`mallsenseai.env`) | root, chmod 600 |
| `/var/lib/mallsenseai/` | 持久数据（postgres、assets） | root |

### 配置文件

`/opt/software/mallsenseai/mallsenseai.env` — 基于 `deploy/mallsenseai.env.example`，安装时自动生成随机密钥：
- `HOST_PORT`: nginx 监听端口（默认 80）
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`: 数据库连接
- `SECRET_KEY`: JWT 签名密钥（自动生成）
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT 过期时间（默认 480 分钟）
- `DATA_DIR`: 持久数据根目录（默认 `/var/lib/mallsenseai`）
- 报警参数：`ALARM_INTERVAL_MINUTES`、`ALARM_THRESHOLD` 等

### 部署脚本

| 脚本 | 用途 | 运行位置 |
|------|------|---------|
| `scripts/install.sh [INSTALL_DIR]` | 全新安装：创建目录→复制文件→构建镜像→启动→迁移→种子用户 | 源码目录 |
| `scripts/uninstall.sh [INSTALL_DIR]` | 停止容器→删除镜像→删除应用文件（保留配置和数据） | 任意位置 |
| `scripts/start.sh` | 启动所有服务并等待健康检查通过 | 安装目录 |
| `scripts/stop.sh` | 停止所有服务（数据保留） | 安装目录 |
| `scripts/update.sh [INSTALL_DIR]` | 备份DB→更新文件→重建镜像→重启→迁移→健康检查 | 源码目录 |
| `scripts/status.sh` | 显示服务状态、健康检查、磁盘用量 | 安装目录 |

### 关键文件

| 文件 | 用途 |
|------|------|
| `Dockerfile` | uv 多阶段构建，Python 3.10，非 root 运行 |
| `docker-compose.yml` | 生产编排：nginx + backend + worker + postgres |
| `docker-compose.dev.yml` | 开发基础设施：仅 PostgreSQL（后端/前端在本地运行） |
| `nginx.conf` | Vue SPA 路由 + `/api` 反向代理 + gzip + 安全头 |
| `.dockerignore` | 排除 `.git`、`node_modules`、`alarm_images`、`*.pt` 等 |
| `deploy/mallsenseai.env.example` | 配置模板，安装脚本复制到 `/opt/software/mallsenseai/` |

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
| e2e | `playwright test` (10 tests, Chromium) | 每次 push/PR 到 main |

### 当前测试覆盖盲区（已知）

- 后端测试用 SQLite，生产用 PostgreSQL+pgvector — 无集成测试
