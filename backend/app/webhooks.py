"""Outbound webhooks — best-effort event notifications so a customer's systems can REACT
to a verdict (fail a CI job on RETIRE, alert Slack on an override). Push, not pull: this
is the one integration the REST API / MCP / SDK can't replace.

Subscribers are operator-configured via GM_WEBHOOK_URLS (comma-separated). If
GM_WEBHOOK_SECRET is set, each payload is signed with HMAC-SHA256 in the X-GM-Signature
header so the receiver can verify authenticity. Delivery NEVER blocks or fails the API
request — a down subscriber is swallowed (fired from a background task). With no
GM_WEBHOOK_URLS configured, emit() is a no-op, so a default deploy is unaffected.

Payload: {"event": "<type>", "ts": "<iso8601>", "data": {...}}
Events:  asset.graded · asset.remediated · asset.overridden
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone


def _subscribers() -> list[str]:
    return [u.strip() for u in os.environ.get("GM_WEBHOOK_URLS", "").split(",") if u.strip()]


def _signature(body: bytes) -> dict[str, str]:
    secret = os.environ.get("GM_WEBHOOK_SECRET")
    if not secret:
        return {}
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-GM-Signature": f"sha256={digest}"}


def emit(event: str, data: dict) -> None:
    """POST {event, ts, data} to every configured subscriber. Best-effort: any delivery
    error is intentionally swallowed so notifications never break grading."""
    urls = _subscribers()
    if not urls:
        return
    body = json.dumps({
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }).encode()
    headers = {"Content-Type": "application/json",
               "User-Agent": "graded-memory-webhook", **_signature(body)}
    for url in urls:
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=5).close()
        except (urllib.error.URLError, OSError, ValueError):
            pass  # a broken/slow subscriber must never break the API request
