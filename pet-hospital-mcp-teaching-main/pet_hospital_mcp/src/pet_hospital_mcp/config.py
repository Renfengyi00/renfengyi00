from __future__ import annotations

import os

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    model_config = ConfigDict(frozen=True)

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8787, ge=1, le=65535)
    pet_hospital_base_url: str = Field(default="http://127.0.0.1:8080")
    request_timeout_seconds: float = Field(default=5.0, gt=0)
    backend_retries: int = Field(default=2, ge=0, le=5)

    @field_validator("pet_hospital_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = AnyHttpUrl(value)
        return str(parsed).rstrip("/")


def load_settings() -> Settings:
    return Settings(
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8787")),
        pet_hospital_base_url=os.getenv("PET_HOSPITAL_BASE_URL", "http://127.0.0.1:8080"),
        request_timeout_seconds=float(os.getenv("PET_HOSPITAL_TIMEOUT_SECONDS", "5.0")),
        backend_retries=int(os.getenv("PET_HOSPITAL_BACKEND_RETRIES", "2")),
    )
