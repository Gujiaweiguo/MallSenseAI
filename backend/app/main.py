from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import alert_workflow, alerts, cameras, dashboard, detection_events, notifications, rois, rules, scenes, users, work_orders
from backend.app.alerts.ws import router as ws_router
from backend.app.auth.router import router as auth_router
from backend.app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.notifications.router import start_notification_router, stop_notification_router
    from backend.app.notifications.service import NotificationService
    from backend.app.alerts.ws import ws_manager
    from backend.app.alerts.events import event_bus
    from backend.app.db.session import SessionLocal

    try:
        service = NotificationService(SessionLocal)
        start_notification_router(service)
    except Exception:
        pass
    ws_manager.start(event_bus)
    yield
    ws_manager.stop(event_bus)
    stop_notification_router()


app = FastAPI(title="MallSenseAI Management API", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})


@app.get("/api/health")
def health_check() -> JSONResponse:
    from sqlalchemy import text
    from backend.app.db.session import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unreachable"},
        )
    return JSONResponse(content={"status": "ok", "database": "connected"})


app.include_router(auth_router, prefix="/api")
app.include_router(ws_router, prefix="/api")
app.include_router(cameras.router, prefix="/api")
app.include_router(scenes.router, prefix="/api")
app.include_router(rois.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(work_orders.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(alert_workflow.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(detection_events.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
