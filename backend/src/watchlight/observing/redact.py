from __future__ import annotations

from typing import Any

_SENSITIVE = ("api_key", "apikey", "secret", "password", "authorization", "token")


class Redactor:
    def redact(self, value: Any, key: str = "") -> Any:
        if key and any(part in key.lower() for part in _SENSITIVE):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {str(k): self.redact(v, str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)
        return value
