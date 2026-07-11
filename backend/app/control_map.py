from __future__ import annotations
from app.models import RiskHit, Grade

_BY_CATEGORY = {
    "secret": ["OWASP LLM02 (Sensitive Info Disclosure)", "NIST AI RMF: MEASURE/MANAGE"],
    "source_code": ["OWASP LLM02 (Sensitive Info Disclosure)", "ISO/IEC 42001 A.8 (data for AI)"],
    "pii": ["EU AI Act Art. 5/50", "Vietnam PDPL 91/2025 (processing log)", "NIST AI RMF: MAP"],
    "unsafe_instruction": ["OWASP LLM01 (Prompt Injection)", "NIST AI RMF: MANAGE"],
}
# Every decision is governance-of-record evidence regardless of grade.
_ALWAYS = ["SR 26-2 (separate GenAI/agentic framework)", "NIST AI RMF: GOVERN"]

def map_controls(grade: Grade, risks: list[RiskHit]) -> list[str]:
    controls: list[str] = list(_ALWAYS)
    for r in risks:
        for c in _BY_CATEGORY.get(r.category, []):
            if c not in controls:
                controls.append(c)
    return controls
