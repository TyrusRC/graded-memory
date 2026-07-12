"""The structured call must survive OpenAI-compatible providers (e.g. Gemini) that
reject the response_format param with a 400 — retry once without it rather than let
the whole grade fall back to offline while the health dot shows green."""
import httpx
from openai import BadRequestError
from pydantic import BaseModel
import app.llm as llm


class _Schema(BaseModel):
    grade: str


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


def _client(create):
    class _Client:
        class chat:
            class completions:
                pass
    _Client.chat.completions.create = staticmethod(create)
    return _Client()


def test_json_complete_retries_without_response_format(monkeypatch):
    calls = []

    def fake_create(**kw):
        calls.append(kw)
        if "response_format" in kw:
            raise BadRequestError(
                "response_format is not supported",
                response=httpx.Response(400, request=httpx.Request("POST", "https://x/v1")),
                body=None,
            )
        return _Resp('{"grade": "KEEP"}')

    monkeypatch.setattr(llm, "build_client", lambda cfg=None: (_client(fake_create), "gemini-2.5-flash"))
    out = llm.json_complete("sys", "user", _Schema)

    assert out.grade == "KEEP"
    assert any("response_format" in c for c in calls)      # tried structured mode first
    assert any("response_format" not in c for c in calls)  # then degraded and succeeded


def test_json_complete_uses_response_format_when_supported(monkeypatch):
    calls = []

    def fake_create(**kw):
        calls.append(kw)
        return _Resp('{"grade": "REVISE"}')

    monkeypatch.setattr(llm, "build_client", lambda cfg=None: (_client(fake_create), "gpt-4o-mini"))
    out = llm.json_complete("sys", "user", _Schema)

    assert out.grade == "REVISE"
    assert len(calls) == 1 and "response_format" in calls[0]  # no needless retry
