"""Google Gemini REST API client with configurable model and resilient error handling."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.config import DEFAULT_GEMINI_MODEL
from backend.utils.errors import ConfigurationError, GeminiAPIError, GeminiQuotaError
from backend.utils.http_client import ResilientHTTPClient


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient:
    """Thin, configurable REST client for Google Gemini content generation."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_GEMINI_MODEL,
        http_client: ResilientHTTPClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = (model or DEFAULT_GEMINI_MODEL).strip()
        self.http = http_client or ResilientHTTPClient()

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        temperature: float = 0.7,
        response_mime_type: str | None = None,
    ) -> str:
        if not self.api_key:
            raise ConfigurationError("GEMINI_API_KEY is not configured. Set it in GitHub Secrets.")

        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        generation_config: dict[str, Any] = {"temperature": temperature}
        if response_mime_type:
            generation_config["responseMimeType"] = response_mime_type

        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            resp = self.http.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json_body=body,
            )
        except Exception as exc:
            raise GeminiAPIError(f"Network error calling Gemini API: {exc}", retryable=True) from exc

        if resp.status_code == 429:
            raise GeminiQuotaError("Gemini API rate limit or quota exceeded (HTTP 429).")
        if resp.status_code in {401, 403}:
            raise GeminiAPIError(
                "Gemini API authentication failed. Verify GEMINI_API_KEY is valid.",
                code="GEMINI_INVALID_KEY",
                retryable=False,
            )
        if resp.status_code >= 400:
            detail = resp.text[:300]
            if "quota" in detail.lower() or "resource_exhausted" in detail.lower():
                raise GeminiQuotaError(f"Gemini quota exhausted: {detail}")
            raise GeminiAPIError(
                f"Gemini API error (HTTP {resp.status_code}): {detail}",
                retryable=resp.status_code >= 500,
            )

        payload = resp.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            raise GeminiAPIError("Gemini API returned no candidates.", retryable=True)
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(str(p.get("text", "")) for p in parts).strip()
        if not text:
            raise GeminiAPIError("Gemini API returned empty content.", retryable=True)
        return text

    def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: str = "",
        temperature: float = 0.5,
    ) -> Any:
        raw = self.generate_text(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
        )
        return self._parse_json_response(raw)

    @staticmethod
    def _parse_json_response(raw: str) -> Any:
        cleaned = raw.strip()
        fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise GeminiAPIError(f"Failed to parse JSON response from Gemini: {exc}") from exc
