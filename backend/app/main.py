from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import alert_workflow, alerts, cameras, rois, rules, scenes, users, work_orders
from backend.app.auth.router import router as auth_router
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="MallSenseAI Management API", docs_url="/docs", redoc_url="/redoc")

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
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api")
app.include_router(cameras.router, prefix="/api")
app.include_router(scenes.router, prefix="/api")
app.include_router(rois.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(work_orders.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(alert_workflow.router, prefix="/api")
