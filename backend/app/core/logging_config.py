import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

SENSITIVE_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"key", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"otp", re.IGNORECASE),
    re.compile(r"cvv", re.IGNORECASE),
]


def redact_sensitive_dict(data: Any) -> Any:
    """Recursively redacts sensitive values from dictionaries and lists."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if any(p.search(str(k)) for p in SENSITIVE_PATTERNS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_dict(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_dict(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """
    Standardized JSON log formatter for production observability.
    Emits clean JSON without leaking secrets or credentials.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom structured attributes if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "tenant_id"):
            log_obj["tenant_id"] = str(record.tenant_id)
        if hasattr(record, "actor_id"):
            log_obj["actor_id"] = str(record.actor_id)
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms

        return json.dumps(redact_sensitive_dict(log_obj))
