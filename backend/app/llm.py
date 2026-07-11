"""Gemini client factory (free tier). One model everywhere: gemini-2.5-flash.
Structured output via response_schema; agentic tools via automatic function calling."""
from __future__ import annotations
import os
import time
from google import genai
from google.genai import errors as genai_errors, types
from dotenv import load_dotenv

load_dotenv()  # picks up GEMINI_API_KEY from .env if present

MODEL = "gemini-2.5-flash"

# One shared client, reused everywhere. The first request pays a one-time
# connection warmup (~seconds); every later call reuses the pooled connection.
# Memoizing also keeps a live reference so the client is never garbage-collected
# mid-call (google-genai's httpx client closes itself in __del__).
_client: genai.Client | None = None


def get_client() -> genai.Client:
    # google-genai reads GEMINI_API_KEY (or GOOGLE_API_KEY) from env.
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
            http_options=types.HttpOptions(timeout=60_000),  # ms; fail a dead connection, don't hang
        )
    return _client


import re

_RETRY_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)


def _violations(e) -> list:
    d = getattr(e, "details", None)
    if not isinstance(d, dict):
        return []
    for detail in d.get("error", {}).get("details", []):
        if detail.get("@type", "").endswith("QuotaFailure"):
            return detail.get("violations", [])
    return []


def _is_daily_exhaustion(e) -> bool:
    """True if the 429 trips a per-day (or zero) quota — waiting won't help today."""
    return any("PerDay" in v.get("quotaId", "") for v in _violations(e))


def _retry_delay(e) -> float | None:
    """Seconds the server asked us to wait, from the RetryInfo detail or message."""
    d = getattr(e, "details", None)
    for detail in (d.get("error", {}).get("details", []) if isinstance(d, dict) else []):
        if detail.get("@type", "").endswith("RetryInfo") and (rd := detail.get("retryDelay")):
            return float(str(rd).rstrip("s"))
    m = _RETRY_RE.search(str(e))
    return float(m.group(1)) if m else None


def with_retry(fn, tries: int = 5, base: float = 2.0):
    """Retry short per-minute throttles, honoring the server's retryDelay.
    Fail fast on a per-day quota exhaustion — it won't reset before the demo."""
    for i in range(tries):
        try:
            return fn()
        except genai_errors.ClientError as e:
            if getattr(e, "code", None) != 429 or i >= tries - 1 or _is_daily_exhaustion(e):
                raise
            wait = _retry_delay(e)
            time.sleep((wait + 1.0) if wait is not None else base * (2 ** i))
