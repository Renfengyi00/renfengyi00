from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from mcp_types import CallToolResult, TextContent
from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BACKEND_TIMEOUT = "BACKEND_TIMEOUT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    BACKEND_API_ERROR = "BACKEND_API_ERROR"
    BACKEND_INVALID_RESPONSE = "BACKEND_INVALID_RESPONSE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorPayload


class ToolFailure(Exception):
    """A sanitized tool execution failure safe to expose to MCP clients."""

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None):
        self.envelope = ErrorEnvelope(
            error=ErrorPayload(code=code, message=message, details=details or {})
        )
        super().__init__(message)


def error_result(code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> CallToolResult:
    envelope = ErrorEnvelope(error=ErrorPayload(code=code, message=message, details=details or {}))
    payload = envelope.model_dump(mode="json")
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=payload,
        is_error=True,
    )
