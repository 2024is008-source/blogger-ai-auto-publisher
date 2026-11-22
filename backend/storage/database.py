"""Optional Supabase PostgREST persistence adapter for multi-user or centralized storage."""

from __future__ import annotations

from typing import Any

from backend.config import AppConfig
from backend.utils.errors import StorageError
from backend.utils.http_client import ResilientHTTPClient


class SupabaseAdapter:
    """Optional Supabase REST client. Operates as a no-op when unconfigured."""

    def __init__(self, config: AppConfig, http_client: ResilientHTTPClient | None = None) -> None:
        self.config = config
        self.http = http_client or ResilientHTTPClient(
            timeout=config.http_timeout_seconds,
            max_retries=config.max_retries,
        )

    @property
    def enabled(self) -> bool:
        return self.config.has_supabase

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.config.supabase_service_role_key,
            "Authorization": f"Bearer {self.config.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation",
        }

    def upsert(self, table: str, record: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        url = f"{self.config.supabase_url}/rest/v1/{table}"
        try:
            resp = self.http.post(url, headers=self._headers(), json_body=record)
        except Exception as exc:
            raise StorageError(f"Supabase connection failed for table '{table}': {exc}", retryable=True) from exc

        if resp.status_code >= 400:
            raise StorageError(
                f"Supabase upsert failed ({resp.status_code}) on '{table}': {resp.text[:250]}",
                retryable=resp.status_code in {429, 500, 502, 503, 504},
            )
        try:
            data = resp.json()
            return data[0] if isinstance(data, list) and data else data
        except Exception:
            return None

    def select_all(self, table: str, limit: int = 200) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        url = f"{self.config.supabase_url}/rest/v1/{table}"
        try:
            resp = self.http.get(url, headers=self._headers(), params={"select": "*", "limit": limit})
        except Exception as exc:
            raise StorageError(f"Supabase read failed for table '{table}': {exc}", retryable=True) from exc

        if resp.status_code >= 400:
            raise StorageError(
                f"Supabase select failed ({resp.status_code}) on '{table}': {resp.text[:250]}",
                retryable=resp.status_code in {429, 500, 502, 503, 504},
            )
        parsed = resp.json()
        return parsed if isinstance(parsed, list) else []
