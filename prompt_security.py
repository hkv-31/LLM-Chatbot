"""Lightweight prompt-injection detection for the LLM chatbot.

This is intentionally a heuristic first line of defense, not a complete
prompt-injection classifier. It detects common high-signal attack patterns,
returns a risk score, and allows normal questions through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityResult:
    suspicious: bool
    score: int
    matched_rules: tuple[str, ...]


# High-signal patterns. The goal is to detect obvious attacks without
# blocking ordinary discussion about prompt injection/security.
RULES: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    (
        "instruction_override",
        3,
        (
            r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
            r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
            r"\bforget\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
        ),
    ),
    (
        "system_prompt_extraction",
        3,
        (
            r"\breveal\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"\bprint\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"\bwhat\s+(?:is|are)\s+(?:your|the)\s+(?:system|developer)\s+(?:prompt|instructions?)\b",
        ),
    ),
    (
        "instruction_nonexistence",
        3,
        (
            r"\bpretend\s+(?:that\s+)?(?:the\s+)?(?:previous|prior|earlier)\s+instructions?\s+(?:do\s+not|don't|never)\s+exist\b",
            r"\b(?:previous|prior|earlier)\s+instructions?\s+(?:do\s+not|don't|never)\s+exist\b",
        ),
    ),
    (
        "untrusted_content_instruction",
        2,
        (
            r"\bfollow\s+(?:the\s+)?instructions?\s+(?:contained|inside|within)\s+(?:this|the)\s+(?:document|file|text|page)\b",
            r"\btreat\s+(?:the\s+)?(?:document|file|text|page)\s+as\s+(?:your\s+)?instructions?\b",
            r"\bthe\s+document\s+(?:above|below)\s+(?:contains|has)\s+instructions?\s+for\s+you\b",
        ),
    ),
    (
        "role_or_policy_override",
        2,
        (
            r"\byou\s+are\s+now\s+(?:a|an)\s+(?:different|unrestricted|unfiltered)\b",
            r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken)\s+(?:assistant|ai|model)\b",
            r"\bignore\s+(?:your\s+)?safety\s+(?:rules|policies|guidelines)\b",
        ),
    ),
    (
        "sensitive_data_exfiltration",
        2,
        (
            r"\breveal\s+(?:the\s+)?(?:api|secret|access)\s+key(?:s)?\b",
            r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:api|secret|access)\s+key(?:s)?\b",
            r"\bexpose\s+(?:internal|private|confidential)\s+(?:information|data|configuration)\b",
        ),
    ),
)

BLOCK_THRESHOLD = 3


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def inspect_prompt(text: str) -> SecurityResult:
    """Inspect one user prompt and return a deterministic security result."""
    normalised = _normalise(text)
    score = 0
    matched: list[str] = []

    for rule_name, weight, patterns in RULES:
        if any(re.search(pattern, normalised) for pattern in patterns):
            score += weight
            matched.append(rule_name)

    return SecurityResult(
        suspicious=score >= BLOCK_THRESHOLD,
        score=score,
        matched_rules=tuple(matched),
    )


def safe_security_message() -> str:
    return (
        "I can help with your question, but I can’t follow requests to "
        "override system instructions, reveal hidden prompts, or expose "
        "private configuration."
    )
