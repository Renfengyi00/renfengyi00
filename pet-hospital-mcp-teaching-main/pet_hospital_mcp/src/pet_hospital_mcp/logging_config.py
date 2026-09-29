from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from typing import Any


SENSITIVE_KEYS = {
    "ownerPhone",
    "ownerAddr",
    "chipNo",
    "owner_phone",
    "owner_addr",
    "chip_no",
}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            redacted[str(key)] = "***REDACTED***" if str(key) in SENSITIVE_KEYS else redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(record.created)),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("tool_name", "params", "status", "duration_ms"):
            if hasattr(record, key):
                payload[key] = redact_sensitive(getattr(record, key))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("pet_hospital_mcp")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def log_tool_call(
    logger: logging.Logger,
    *,
    tool_name: str,
    params: dict[str, Any],
    status: str,
    duration_ms: float,
) -> None:
    logger.info(
        "tool_call",
        extra={
            "tool_name": tool_name,
            "params": redact_sensitive(params),
            "status": status,
            "duration_ms": round(duration_ms, 2),
        },
    )
