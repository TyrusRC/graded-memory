"""Deterministic detection of the three leak vectors + unsafe instructions.
Heuristics are intentionally noisy — the Judge reasons over these hits, it does
not blindly trust them (see spec 3c). Regex + Shannon entropy + light code/PII
signatures. NEVER put real secrets here; demo data is synthetic."""
from __future__ import annotations
import math
import re
from app.models import RiskHit

# --- secrets -----------------------------------------------------------------
_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"(?:postgres|mysql|mongodb|redis)://[^:\s]+:[^@\s]+@[^\s/]+", "DB URI with credentials"),
    (r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{12,}", "hardcoded credential"),
]

def _shannon(s: str) -> float:
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    return -sum((n/len(s)) * math.log2(n/len(s)) for n in counts.values())

# --- source code -------------------------------------------------------------
_CODE_SIGNS = [
    r"\bdef\s+\w+\s*\(", r"\bclass\s+\w+", r"\bimport\s+\w+", r"\bfrom\s+\w+\s+import",
    r"\bfunction\s+\w+\s*\(", r"=>", r"\bpublic\s+(?:static\s+)?\w+\s+\w+\s*\(",
    r"\breturn\b.*;", r"#include\s*<",
]

# --- pii ---------------------------------------------------------------------
_PII_PATTERNS: list[tuple[str, str]] = [
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "email"),
    (r"\b(?:\+?84|0)(?:3|5|7|8|9)\d{8}\b", "VN phone"),
    (r"\b\d{12}\b", "VN national id (CCCD)"),
    (r"\b(?:\d[ -]?){13,16}\b", "payment card number"),
]

# --- unsafe instructions -----------------------------------------------------
_UNSAFE = [
    r"(?i)ignore (?:all|any|previous) .{0,20}instructions",
    r"(?i)\bdrop\s+table\b", r"(?i)\bdelete\s+from\b", r"(?i)\bexport\b.{0,30}\b(?:users|customers|accounts)\b",
    r"(?i)disable .{0,20}(?:auth|validation|guardrail)",
]

# --- agentic data-exfiltration / risky bulk actions --------------------------
# An agent told to mass-pull docs/files/repos, or to push/send data to an
# external or personal destination. These risks are semantic, not syntactic:
# the live LLM reasons about the subtle cases, these catch the blatant ones
# even offline. (severity: bulk pull -> medium/REVISE; exfiltration -> high/RETIRE)
_EXFIL_PATTERNS: list[tuple[str, str, str]] = [
    (r"(?i)\b(?:download|scrape|export|pull|dump|clone|copy|sync|collect|harvest)\b[^.\n]{0,60}\b(?:all|every|entire|bulk|each)\b[^.\n]{0,40}\b(?:docs?|documents?|files?|pages?|repos?|repositories|records?|data|tables?|customers?|users?)\b",
     "bulk data pull", "medium"),
    (r"(?i)\b(?:push|upload|send|forward|post|exfiltrate|leak|transfer|sync|copy)\b[^.\n]{0,60}\b(?:github|gitlab|bitbucket|dropbox|google\s*drive|gdrive|s3|pastebin|telegram|personal|external|my\s+(?:own\s+)?(?:email|inbox|repo(?:sitory)?|drive|account|server|laptop))\b",
     "exfiltration to external/personal destination", "high"),
]

# --- offensive / abusive security instructions -------------------------------
# Instructions to attack, intrude on, or disrupt systems. Authorized pentesting
# is legitimate, so reconnaissance alone is medium (REVISE — confirm scope /
# sign-off); explicit exploitation, intrusion, malware, or disruption is high
# (RETIRE). Objects are network-specific so business jargon ("exploit synergies",
# "scan the document") does not trip these. The live LLM weighs authorization;
# these catch the blatant asks even offline.
_OFFENSIVE_PATTERNS: list[tuple[str, str, str]] = [
    (r"(?i)\bexploit\w*\b[^.\n]{0,40}\b(?:vulnerabilit\w+|weakness\w*|cve|system\w*|server\w*|host\w*|network\w*|target\w*|machine\w*|ports?|application\w*|service\w*)\b",
     "exploitation instruction", "high"),
    (r"(?i)\b(?:vulnerabilit\w+|weakness(?:es)?|cve|foothold)\b[^.\n]{0,40}\b(?:exploit\w*|attack\w*|compromis\w*|breach\w*|pwn\w*)\b",
     "exploitation instruction", "high"),
    (r"(?i)\b(?:hack\w*|break\s+in(?:to)?|compromis\w*|breach\w*|pwn\w*|gain\s+(?:unauthoriz\w+\s+)?access|privilege\s+escalat\w*|escalate\s+privileg\w*|plant\s+a?\s*backdoor)\b[^.\n]{0,40}\b(?:system\w*|server\w*|host\w*|network\w*|account\w*|machine\w*|database\w*|infrastructure|target\w*|compan\w*|corporate)\b",
     "intrusion instruction", "high"),
    (r"(?i)\b(?:ddos|denial[\s-]of[\s-]service|brute[\s-]?forc\w*|password[\s-]?spray\w*)\b",
     "disruption/credential attack", "high"),
    (r"(?i)\b(?:deploy|install|write|build|create|drop)\b[^.\n]{0,30}\b(?:malware|ransomware|rootkit|keylogger|trojan|botnet|worm|spyware)\b",
     "malware instruction", "high"),
    (r"(?i)\b(?:scan|enumerate|probe|fingerprint|sweep)\b[^.\n]{0,30}\b(?:all\s+|every\s+)?(?:ports?|hosts?|subnets?|networks?|targets?|ip\s+ranges?|services?)\b",
     "network reconnaissance", "medium"),
]

def scan(text: str) -> list[RiskHit]:
    hits: list[RiskHit] = []

    for pat, detail in _SECRET_PATTERNS:
        for m in re.findall(pat, text):
            frag = m if isinstance(m, str) else m[0]
            hits.append(RiskHit(category="secret", match=frag[:80], severity="high", detail=detail))

    # entropy catch for long high-randomness tokens not already flagged
    for token in re.findall(r"[A-Za-z0-9/+_=-]{20,}", text):
        if _shannon(token) > 4.0 and not any(token[:12] in h.match for h in hits):
            hits.append(RiskHit(category="secret", match=token[:80], severity="medium",
                                detail="high-entropy string"))

    code_signals = sum(1 for pat in _CODE_SIGNS if re.search(pat, text))
    if code_signals >= 2:
        hits.append(RiskHit(category="source_code", match=text[:80], severity="high",
                            detail=f"{code_signals} code signatures"))

    for pat, detail in _PII_PATTERNS:
        for m in re.findall(pat, text):
            frag = m if isinstance(m, str) else "".join(m)
            hits.append(RiskHit(category="pii", match=str(frag)[:80], severity="medium", detail=detail))

    for pat in _UNSAFE:
        m = re.search(pat, text)
        if m:
            hits.append(RiskHit(category="unsafe_instruction", match=m.group(0)[:80],
                                severity="high", detail="policy-violating instruction"))

    for pat, detail, sev in _EXFIL_PATTERNS:
        m = re.search(pat, text)
        if m:
            hits.append(RiskHit(category="unsafe_instruction", match=m.group(0)[:80],
                                severity=sev, detail=detail))

    for pat, detail, sev in _OFFENSIVE_PATTERNS:
        m = re.search(pat, text)
        if m:
            hits.append(RiskHit(category="unsafe_instruction", match=m.group(0)[:80],
                                severity=sev, detail=detail))

    # de-dupe by (category, match)
    seen: set[tuple[str, str]] = set()
    out: list[RiskHit] = []
    for h in hits:
        k = (h.category, h.match)
        if k not in seen:
            seen.add(k)
            out.append(h)
    return out


# --- redact-before-LLM ------------------------------------------------------
# Mask every detected leak so raw secrets/PII/source-code never leave the
# perimeter (never reach the offshore grading model). Detection stays local.
_PLACEHOLDER = {
    "secret": "⟦REDACTED-SECRET⟧",
    "pii": "⟦REDACTED-PII⟧",
    "source_code": "⟦REDACTED-CODE⟧",
    "unsafe_instruction": "⟦FLAGGED-INSTRUCTION⟧",
}

def _looks_code(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if any(re.search(pat, line) for pat in _CODE_SIGNS):
        return True
    # indented statement/call lines (over-masking is safe — it just sends less to the model)
    if line[:1] in (" ", "\t") and (("(" in s and ")" in s) or s.endswith(":") or ";" in s or "=" in s):
        return True
    return False

def redact(text: str) -> str:
    """Return text with every scan() hit masked. Secrets/PII/unsafe are replaced
    by exact substring; source code is masked line-by-line (spans are unbounded)."""
    hits = scan(text)
    out = text
    for h in hits:
        if h.category in ("secret", "pii", "unsafe_instruction"):
            out = out.replace(h.match, _PLACEHOLDER[h.category])
    if any(h.category == "source_code" for h in hits):
        out = "\n".join(_PLACEHOLDER["source_code"] if _looks_code(ln) else ln
                        for ln in out.splitlines())
    return out
