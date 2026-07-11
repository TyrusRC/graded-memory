"""Webhooks are best-effort and must never break a request: no subscribers -> no-op, a
down subscriber is swallowed, and a configured subscriber gets a signed payload."""
import hashlib
import hmac
import json
import urllib.request
import app.webhooks as wh


class _FakeResp:
    def close(self):
        pass


def test_no_subscribers_is_noop(monkeypatch):
    monkeypatch.delenv("GM_WEBHOOK_URLS", raising=False)
    called = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: called.append(1))
    wh.emit("asset.graded", {"grade": "KEEP"})     # must not raise
    assert called == []                             # and must not attempt delivery


def test_emit_posts_signed_payload(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = req.data
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("GM_WEBHOOK_URLS", "https://example.com/hook")
    monkeypatch.setenv("GM_WEBHOOK_SECRET", "s3cret")

    wh.emit("asset.graded", {"grade": "RETIRE", "prompt_id": "p1"})

    assert captured["url"] == "https://example.com/hook"
    payload = json.loads(captured["body"])
    assert payload["event"] == "asset.graded"
    assert payload["data"]["grade"] == "RETIRE"
    assert "ts" in payload
    expected = "sha256=" + hmac.new(b"s3cret", captured["body"], hashlib.sha256).hexdigest()
    assert captured["headers"]["x-gm-signature"] == expected


def test_unsigned_when_no_secret(monkeypatch):
    captured = {}
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None: captured.update(
                            headers={k.lower() for k, _ in req.header_items()}) or _FakeResp())
    monkeypatch.setenv("GM_WEBHOOK_URLS", "https://example.com/hook")
    monkeypatch.delenv("GM_WEBHOOK_SECRET", raising=False)
    wh.emit("asset.overridden", {"prompt_id": "p1"})
    assert "x-gm-signature" not in captured["headers"]


def test_delivery_error_is_swallowed(monkeypatch):
    def boom(req, timeout=None):
        raise OSError("subscriber down")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setenv("GM_WEBHOOK_URLS", "https://example.com/hook")
    wh.emit("asset.graded", {"grade": "KEEP"})     # must not raise


def test_grade_endpoint_fires_webhook(monkeypatch):
    calls = []
    monkeypatch.setattr("app.webhooks.emit", lambda event, data: calls.append((event, data)))
    from fastapi.testclient import TestClient
    from app.main import app
    TestClient(app).post("/api/grade", json={"text": "ship it with AKIAIOSFODNN7EXAMPLE now"})
    assert any(e == "asset.graded" and d["grade"] == "RETIRE" for e, d in calls)
