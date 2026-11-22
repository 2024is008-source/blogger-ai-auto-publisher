#!/usr/bin/env python3
"""Local one-time Google OAuth 2.0 setup helper for Blogger API v3.

Run this script on your local machine to authorize your Google Blogger account
and print a BLOGGER_REFRESH_TOKEN to paste directly into GitHub Secrets.
Never commit credentials or tokens into the repository.
"""

from __future__ import annotations

import http.server
import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/blogger"
REDIRECT_URI = "http://127.0.0.1:8765/oauth2callback"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    auth_code: str = ""
    error: str = ""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "error" in params:
            _CallbackHandler.error = params["error"][0]
        elif "code" in params:
            _CallbackHandler.auth_code = params["code"][0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authorization received.</h2>"
            b"<p>You may close this tab and return to your terminal.</p></body></html>"
        )

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    client_id = os.getenv("GOOGLE_CLIENT_ID") or input("Enter GOOGLE_CLIENT_ID: ").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or input("Enter GOOGLE_CLIENT_SECRET: ").strip()
    if not client_id or not client_secret:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required.", file=sys.stderr)
        return 1

    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    url = f"{AUTH_URL}?{query}"
    print("\nOpening browser for Google Blogger OAuth authorization...")
    print(f"If the browser does not open automatically, visit:\n{url}\n")
    webbrowser.open(url)

    server = http.server.HTTPServer(("127.0.0.1", 8765), _CallbackHandler)
    server.handle_request()

    if _CallbackHandler.error:
        print(f"Authorization error: {_CallbackHandler.error}", file=sys.stderr)
        return 1
    if not _CallbackHandler.auth_code:
        print("No authorization code received.", file=sys.stderr)
        return 1

    data = urllib.parse.urlencode(
        {
            "code": _CallbackHandler.auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        print(
            "Warning: Google did not return a refresh_token. "
            "Revoke prior access in Google Account Security and retry with prompt=consent.",
            file=sys.stderr,
        )
        return 1

    print("\nSuccess! Copy this value into GitHub Repository Secret `BLOGGER_REFRESH_TOKEN`:")
    print("-" * 72)
    print(refresh_token)
    print("-" * 72)
    print("Do NOT commit this token into any repository file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
