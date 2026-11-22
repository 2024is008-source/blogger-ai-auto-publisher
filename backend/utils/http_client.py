"""Resilient HTTP client with exponential backoff, retries, and timeout enforcement."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class HTTPResponse:
    status_code: int
    body: bytes
    headers: dict[str, str]

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


class ResilientHTTPClient:
    """Zero-dependency HTTP client using urllib with exponential backoff.

    Supports dependency injection of `transport` for deterministic unit testing.
    """

    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        transport: Callable[..., HTTPResponse] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._transport = transport or self._default_transport
        self._sleep = sleep_fn

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: Any | None = None,
        data: bytes | dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> HTTPResponse:
        full_url = url
        if params:
            encoded = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
            sep = "&" if "?" in full_url else "?"
            full_url = f"{full_url}{sep}{encoded}"

        req_headers = {"User-Agent": "BloggerAIAutoPublisher/1.0 (+https://github.com)"}
        if headers:
            req_headers.update(headers)

        payload: bytes | None = None
        if json_body is not None:
            payload = json.dumps(json_body).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, dict):
            payload = urllib.parse.urlencode(data).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(data, bytes):
            payload = data

        attempt = 0
        last_exc: Exception | None = None
        while attempt <= self.max_retries:
            try:
                resp = self._transport(
                    method=method.upper(),
                    url=full_url,
                    headers=req_headers,
                    body=payload,
                    timeout=timeout or self.timeout,
                )
                if resp.status_code in self.RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    delay = self.backoff_base * (2**attempt)
                    self._sleep(delay)
                    attempt += 1
                    continue
                return resp
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise
                delay = self.backoff_base * (2**attempt)
                self._sleep(delay)
                attempt += 1

        if last_exc:
            raise last_exc
        raise RuntimeError("HTTP request failed unexpectedly")

    def get(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> HTTPResponse:
        return self.request("HEAD", url, **kwargs)

    @staticmethod
    def _default_transport(
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: int,
    ) -> HTTPResponse:
        req = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return HTTPResponse(
                    status_code=resp.getcode() or 200,
                    body=resp.read(),
                    headers={k.lower(): v for k, v in resp.headers.items()},
                )
        except urllib.error.HTTPError as err:
            return HTTPResponse(
                status_code=err.code,
                body=err.read() if err.fp else b"",
                headers={k.lower(): v for k, v in (err.headers.items() if err.headers else [])},
            )
