"""Provider-agnostic, bring-your-own-key LLM adapter (OpenAI-compatible Chat
Completions).

There is NO baked-in key. Each request may carry its own provider config (base URL,
key, model) — sent by the user from the browser and used only for that call, never
stored or logged. An operator may also set env defaults (LLM_BASE_URL / LLM_API_KEY /
LLM_MODEL). With neither, the app grades deterministically offline.

Works with any OpenAI-compatible endpoint (QwenCloud, Featherless, OpenAI, Kimi, or
Gemini's OpenAI-compatible endpoint). Structured output via JSON mode + Pydantic.
The safety-critical scan/gate stays deterministic (judge.py); this layer only adds
rubric nuance, agentic reasoning, and remediation."""
from __future__ import annotations
import ipaddress
import os
import socket
import time
from urllib.parse import urlparse
from openai import OpenAI, OpenAIError, RateLimitError, BadRequestError
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()  # picks up LLM_* env defaults if present

_ENV_MODEL = os.environ.get("LLM_MODEL", "qwen-plus")
_ENV_BASE_URL = os.environ.get("LLM_BASE_URL")
_ENV_API_KEY = os.environ.get("LLM_API_KEY")

# Any of these trips the deterministic fallback instead of a 500 on stage: an SDK/API
# error, or a malformed-JSON / schema-mismatch response from the model.
LLMError = (OpenAIError, ValidationError, ValueError)


class LLMConfig(BaseModel):
    """Per-request, user-supplied provider config (bring-your-own-key)."""
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


def _resolve(cfg: LLMConfig | None) -> tuple[str | None, str | None, str]:
    base = (cfg.base_url if cfg and cfg.base_url else _ENV_BASE_URL)
    key = (cfg.api_key if cfg and cfg.api_key else _ENV_API_KEY)
    model = (cfg.model if cfg and cfg.model else _ENV_MODEL)
    return base, key, model


def has_llm(cfg: LLMConfig | None = None) -> bool:
    """True when a provider (per-request or env) is configured; else grade offline."""
    base, key, _ = _resolve(cfg)
    return bool(base and key)


def resolved_model(cfg: LLMConfig | None = None) -> str:
    """The model name that a call with this config would actually use (for audit)."""
    return _resolve(cfg)[2]


def is_safe_base_url(url: str) -> bool:
    """SSRF guard: the backend must only call out to a public HTTPS host. Blocks
    http, and any loopback / private / link-local / reserved address (incl. cloud
    metadata endpoints), since the base URL is user-supplied."""
    try:
        u = urlparse(url)
        if u.scheme != "https" or not u.hostname:
            return False
        infos = socket.getaddrinfo(u.hostname, u.port or 443, proto=socket.IPPROTO_TCP)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
        return bool(infos)
    except (OSError, ValueError):
        return False


def with_retry(fn, tries: int = 4, base: float = 1.5):
    """Retry only rate-limit throttles with exponential backoff; surface everything else."""
    for i in range(tries):
        try:
            return fn()
        except RateLimitError:
            if i >= tries - 1:
                raise
            time.sleep(base * (2**i))


def _extract_json(content: str) -> str:
    """Be lenient about providers that wrap JSON in code fences or prose."""
    content = content.strip()
    if "{" in content and "}" in content:
        return content[content.index("{"): content.rindex("}") + 1]
    return content


def build_client(cfg: LLMConfig | None = None) -> tuple[OpenAI, str]:
    """Construct an OpenAI-compatible client from resolved config, or raise ValueError
    (an LLMError member) if no provider is configured or the base URL fails the SSRF
    guard. Returns (client, model)."""
    base, key, model = _resolve(cfg)
    if not (base and key):
        raise ValueError("no LLM provider configured")
    if not is_safe_base_url(base):
        raise ValueError("unsafe LLM base URL (must be a public https host)")
    return OpenAI(base_url=base, api_key=key, timeout=60, max_retries=0), model


def json_complete(system: str, user: str, schema: type[BaseModel], cfg: LLMConfig | None = None):
    """One structured call: ask for JSON, validate into `schema`, return the model.
    Raises an LLMError member on API failure or an unparseable/invalid response."""
    client, model = build_client(cfg)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]

    def _create(**extra):
        return with_retry(lambda: client.chat.completions.create(
            model=model, messages=messages, temperature=0, **extra))

    try:
        resp = _create(response_format={"type": "json_object"})
    except BadRequestError:
        # Some OpenAI-compatible providers (notably Gemini's endpoint) reject the
        # response_format param with a 400. The system prompt already demands a JSON
        # object and _extract_json tolerates fences/prose, so retry without it.
        resp = _create()

    content = _extract_json(resp.choices[0].message.content or "")
    return schema.model_validate_json(content)


def ping(cfg: LLMConfig | None = None) -> str:
    """Green-dot health check: prove the configured provider actually answers. Makes a
    tiny 1-token completion; returns the model name on success, raises an LLMError
    member (unconfigured, unsafe URL, auth failure, outage) otherwise."""
    client, model = build_client(cfg)
    with_retry(lambda: client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1,
        temperature=0,
    ))
    return model
