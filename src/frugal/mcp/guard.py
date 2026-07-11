"""Guardrails used by the MCP middleware (and usable standalone):
PII redaction + a cheap prompt-injection sniff. Regex-based, offline, fast —
a first line of defence, not a replacement for a real security review.
"""
from __future__ import annotations

import re
from typing import Dict, List

_PII_PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "api_key": re.compile(r"\b(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16})\b"),
    "phone": re.compile(r"\+?\d[\d\s().-]{8,}\d"),
}

_INJECTION_SIGNALS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "you are now",
    "system prompt",
    "reveal your instructions",
    "print your system prompt",
)


def redact_pii(text: str) -> Dict[str, object]:
    found: Dict[str, int] = {}
    out = text
    for label, pat in _PII_PATTERNS.items():
        matches = pat.findall(out)
        if matches:
            found[label] = len(matches)
            out = pat.sub(f"[REDACTED_{label.upper()}]", out)
    return {"redacted": out, "found": found}


def detect_injection(text: str) -> List[str]:
    low = text.lower()
    return [s for s in _INJECTION_SIGNALS if s in low]


def guard_prompt(text: str) -> Dict[str, object]:
    pii = redact_pii(text)
    injections = detect_injection(text)
    return {
        "safe": not injections,
        "redacted_prompt": pii["redacted"],
        "pii_found": pii["found"],
        "injection_signals": injections,
    }
