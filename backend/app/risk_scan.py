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
    # modern vendor-prefixed keys (specific formats -> negligible false positives)
    (r"sk-proj-[A-Za-z0-9_-]{16,}", "OpenAI project key"),
    (r"sk-[A-Za-z0-9]{32,}", "OpenAI API key"),
    (r"sk_(?:live|test)_[A-Za-z0-9]{16,}", "Stripe secret key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
    (r"AIza[A-Za-z0-9_-]{35}", "Google API key"),
    (r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{12,}", "hardcoded credential"),
    # credential stated in prose ("the password is X"): require a mixed digit+letter
    # value so "the password is required" and similar plain words don't trip it.
    (r"(?i)\b(?:password|passwd|pwd|secret|api[ _-]?key|access[ _-]?token|token)\b[^.\n]{0,40}?(?:\bis\b|=|:)\s+['\"]?(?=[^\s'\"]*[0-9])(?=[^\s'\"]*[A-Za-z])[^\s'\"]{8,}", "credential in prose"),
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
    (r"(?i)\b(?:push|upload|send|forward|post|exfiltrate|leak|transfer|sync|copy|e-?mail|mail)\b[^.\n]{0,60}\b(?:github|gitlab|bitbucket|dropbox|google\s*drive|gdrive|s3|pastebin|telegram|whatsapp|outlook|hotmail|gmail|proton\w*|icloud|yahoo|gmx|thumb\s*drive|flash\s*drive|usb(?:\s*(?:stick|drive))?|sd\s*card|competitor|rival|recruiter|personal|external|(?:my|private)\s+(?:own\s+)?(?:email|inbox|repo(?:sitory)?|drive|account|server|laptop|address))\b",
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

# --- other abusive / policy-violating instructions ---------------------------
# Whole classes an agentic prompt library must quarantine: destructive data ops
# beyond DROP/DELETE, jailbreak/prompt-injection variants, social engineering,
# compliance-control bypass, and moving regulated data off-perimeter. Objects are
# scoped so ordinary business phrasing ("overwrite the draft file", "pretend to be
# a helpful support agent") does not trip these. All high -> RETIRE.
_ABUSE_PATTERNS: list[tuple[str, str, str]] = [
    # destructive data / infrastructure operations
    (r"(?i)\btruncate\s+table\b", "destructive data operation", "high"),
    (r"(?i)\b(?:delete|update)\b[^.\n]{0,40}\bwhere\s+1\s*=\s*1\b", "destructive data operation", "high"),
    (r"(?i)\brm\s+-rf\b|\bmkfs\b|\bdd\s+if=|>\s*/dev/sd", "destructive shell command", "high"),
    (r"(?i)\b(?:wipe|erase|purge|destroy|nuke|obliterate|overwrite)\b[^.\n]{0,30}\b(?:records?|databases?|users?|accounts?|tables?|backups?|balances?|column)\b", "destructive data operation", "high"),
    (r"(?i)\b(?:reset|restore)\b[^.\n]{0,20}\bfactory\b", "destructive reset", "high"),
    # prompt injection / jailbreak (beyond 'ignore previous instructions')
    (r"(?i)\b(?:disregard|forget|override|ignore|bypass)\b[^.\n]{0,25}\b(?:instructions?|rules?|guidelines?|policy|policies|prompt|restrictions?)\b", "jailbreak / prompt injection", "high"),
    (r"(?i)\bdeveloper\s+mode\b|\bjailbr(?:oken|eak)\b|\bunfiltered\b", "jailbreak / prompt injection", "high"),
    (r"(?i)\bno\s+(?:content\s+)?(?:policy|rules|restrictions|filter|guardrails)\b", "jailbreak / prompt injection", "high"),
    (r"(?i)\brestrictions?\s+(?:are\s+)?(?:lifted|removed|disabled|turned\s+off|off)\b", "jailbreak / prompt injection", "high"),
    (r"(?i)\bwithout\s+(?:any\s+)?(?:filter|restriction|censorship|guardrails?)\b", "jailbreak / prompt injection", "high"),
    (r"(?i)\b(?:pretend|assume|imagine)\b[^.\n]{0,30}\b(?:safety|guidelines?|rules?|policy|restrictions?)\b[^.\n]{0,20}\b(?:do\s+not|don'?t|no\s+longer|never)\b", "jailbreak / prompt injection", "high"),
    # social engineering / phishing / credential harvesting
    (r"(?i)\bphishing\b|\bspear[\s-]?phish\w*\b", "social engineering / phishing", "high"),
    (r"(?i)\bimpersonat\w+\b", "impersonation / social engineering", "high"),
    (r"(?i)\bfake\s+(?:login|sign[\s-]?in|portal|page|website)\b", "credential-harvesting page", "high"),
    (r"(?i)\b(?:harvest|capture|steal|phish|grab)\b[^.\n]{0,25}\b(?:credentials?|passwords?|logins?|otp|2fa)\b", "credential theft", "high"),
    (r"(?i)\b(?:pretend\w*\s+to\s+be|pos(?:e|ing)\s+as)\b[^.\n]{0,60}\b(?:reset|password|credentials?|wire\s+transfer|gain\s+access|verify\s+(?:the\s+)?account)\b", "pretexting / social engineering", "high"),
    # offensive post-exploitation
    (r"(?i)\blateral\s+movement\b|\bpass[\s-]the[\s-](?:hash|ticket)\b|\bprivilege\s+escalat\w+\b", "offensive post-exploitation", "high"),
    # compliance / control bypass
    (r"(?i)\b(?:skip|bypass|omit|ignore|circumvent|disable|avoid)\b[^.\n]{0,25}\b(?:kyc|aml|identity\s+verification|due\s+diligence|sanctions?\s+(?:screening|check|list)|compliance\s+(?:check|review)|background\s+check)\b", "compliance / control bypass", "high"),
    # regulated / personal data moved to a third party
    (r"(?i)\b(?:share|send|disclose|hand\s+over|give|upload|export|email|sell|provide)\b[^.\n]{0,50}\b(?:medical|patient|health|phi|pii|ssn|social\s+security|customer\s+(?:data|records?|pii|list)|personal\s+data|payroll)\b[^.\n]{0,50}\b(?:third[\s-]?party|external|vendor|startup|partner|competitor|rival|another\s+company)\b", "regulated data to third party", "high"),
    # mass collection of sensitive identifiers
    (r"(?i)\b(?:compile|collect|gather|list|extract|scrape|pull|build\s+a\s+list\s+of)\b[^.\n]{0,50}\b(?:ssn|social\s+security|home\s+address(?:es)?|dates?\s+of\s+birth|dob|passport|hiv|diagnos\w+)\b", "mass sensitive-data collection", "high"),
    # physical exfiltration channel
    (r"(?i)\b(?:print(?:\s*out)?|take|carry|walk\s+out|smuggle|remove)\b[^.\n]{0,45}\b(?:home|off[\s-]?site|out\s+of\s+the\s+(?:office|company|building)|thumb\s*drive|flash\s*drive|usb\s*(?:stick|drive)?|sd\s*card)\b", "physical exfiltration", "high"),
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

    for pat, detail, sev in _ABUSE_PATTERNS:
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
