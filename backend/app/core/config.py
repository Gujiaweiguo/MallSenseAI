from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = True
    database_url: str = "sqlite:///./data/mallsenseai_dev.db"
    secret_key: str = Field(default="", min_length=0)
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5373"])

    alarm_threshold: int = 3000
    alarm_interval_minutes: int = 1
    alarm_static_wait_minutes: int = 1
    alarm_diff_threshold: int = 18
    alarm_enable_yolo_detection: bool = True
    alarm_enable_image_comparison: bool = True
    alarm_detection_mode: Literal["max", "sum", "yolo_only", "image_only"] = "max"

    # Fire / smoke detector
    fire_smoke_check_interval_seconds: int = 15
    fire_smoke_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def enforce_prod_database(cls, value: str, info) -> str:
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and value.startswith("sqlite"):
            raise ValueError("Production must use PostgreSQL, not SQLite")
        return value

    @property
    def alarm_config_overrides(self) -> dict[str, object]:
        return {
            "threshold": self.alarm_threshold,
            "interval_minutes": self.alarm_interval_minutes,
            "static_wait_minutes": self.alarm_static_wait_minutes,
            "diff_threshold": self.alarm_diff_threshold,
            "enable_yolo_detection": self.alarm_enable_yolo_detection,
            "enable_image_comparison": self.alarm_enable_image_comparison,
            "detection_mode": self.alarm_detection_mode,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
