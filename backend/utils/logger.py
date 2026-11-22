"""Structured logging with automatic secret redaction and persistent log records."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_TOKEN_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"(AIza[0-9A-Za-z\-_]{20,})"),
    re.compile(r"(ya29\.[0-9A-Za-z\-_]+)"),
    re.compile(r"(ghp_[0-9A-Za-z]{20,})"),
    re.compile(r"(github_pat_[0-9A-Za-z_]{20,})"),
    re.compile(r"([?&](?:key|api_key|access_token|client_secret|refresh_token)=)([^&\s]+)", re.IGNORECASE),
]


def redact_secrets(text: str, extra_secrets: list[str] | None = None) -> str:
    """Scrub known secret patterns and runtime credentials from text."""
    sanitized = str(text)
    if extra_secrets:
        for secret in extra_secrets:
            if secret and len(secret) >= 4:
                sanitized = sanitized.replace(secret, "[REDACTED]")
    sanitized = _TOKEN_PATTERNS[0].sub(r"\1[REDACTED]", sanitized)
    for pat in _TOKEN_PATTERNS[1:5]:
        sanitized = pat.sub("[REDACTED]", sanitized)
    sanitized = _TOKEN_PATTERNS[5].sub(r"\1[REDACTED]", sanitized)
    return sanitized


class StructuredLogger:
    """Writes secret-redacted JSON log lines to stderr and optional data/logs.json."""

    def __init__(
        self,
        name: str = "blogger_ai_publisher",
        *,
        secrets: list[str] | None = None,
        log_file: Path | None = None,
        max_persisted_entries: int = 500,
    ) -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
        self._secrets = secrets or []
        self._log_file = log_file
        self._max_persisted_entries = max_persisted_entries

    def log(self, level: str, component: str, message: str, **context: Any) -> dict[str, Any]:
        safe_msg = redact_secrets(message, self._secrets)
        safe_ctx: dict[str, Any] = {}
        for k, v in context.items():
            if any(tok in k.lower() for tok in ("secret", "token", "password", "api_key", "authorization")):
                safe_ctx[k] = "[REDACTED]"
            else:
                safe_ctx[k] = redact_secrets(json.dumps(v) if isinstance(v, (dict, list)) else str(v), self._secrets)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "component": component,
            "message": safe_msg,
            "context": safe_ctx,
        }
        line = json.dumps(entry, ensure_ascii=False)
        lvl = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(lvl, line)

        if self._log_file is not None:
            self._append_to_file(entry)
        return entry

    def info(self, component: str, message: str, **context: Any) -> dict[str, Any]:
        return self.log("INFO", component, message, **context)

    def warning(self, component: str, message: str, **context: Any) -> dict[str, Any]:
        return self.log("WARNING", component, message, **context)

    def error(self, component: str, message: str, **context: Any) -> dict[str, Any]:
        return self.log("ERROR", component, message, **context)

    def _append_to_file(self, entry: dict[str, Any]) -> None:
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            entries: list[dict[str, Any]] = []
            if self._log_file.exists():
                raw = self._log_file.read_text(encoding="utf-8").strip()
                if raw:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        entries = parsed
            entries.append(entry)
            if len(entries) > self._max_persisted_entries:
                entries = entries[-self._max_persisted_entries :]
            self._log_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
