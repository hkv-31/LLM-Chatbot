"""Lightweight prompt-injection detection for the LLM chatbot.

This is a heuristic first-line defense, not a complete prompt-injection
classifier. It detects common high-signal attack patterns, returns a risk
score, and allows normal questions through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityResult:
    suspicious: bool
    score: int
    matched_rules: tuple[str, ...]


# Each rule has:
#   name
#   weight
#   regex patterns
#
# The detector intentionally focuses on high-confidence attack language
# rather than individual words such as "prompt", "document", or "API".
RULES: tuple[tuple[str, int, tuple[str, ...]], ...] = (

    # ---------------------------------------------------------
    # 1. Instruction override
    # ---------------------------------------------------------
    (
        "instruction_override",
        3,
        (
            r"\bignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
            r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
            r"\bforget\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?\b",
            r"\bignore\s+(?:the\s+)?application\s+rules?\b",
        ),
    ),

    # ---------------------------------------------------------
    # 2. System/developer prompt extraction
    # ---------------------------------------------------------
    (
        "system_prompt_extraction",
        3,
        (
            r"\breveal\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"\bprint\s+(?:the\s+)?(?:system|developer)\s+(?:prompt|instructions?)\b",
            r"\bwhat\s+(?:is|are)\s+(?:your|the)\s+(?:system|developer)\s+(?:prompt|instructions?)\b",

            # Hidden prompt variants
            r"\breveal\s+(?:your\s+)?hidden\s+prompt\b",
            r"\bshow\s+(?:me\s+)?(?:your\s+)?hidden\s+prompt\b",
            r"\bexpose\s+(?:your\s+)?hidden\s+prompt\b",
        ),
    ),

    # ---------------------------------------------------------
    # 3. Attempt to invalidate previous instructions
    # ---------------------------------------------------------
    (
        "instruction_nonexistence",
        3,
        (
            r"\bpretend\s+(?:that\s+)?(?:the\s+)?(?:previous|prior|earlier)\s+instructions?\s+(?:do\s+not|don't|never)\s+exist\b",
            r"\b(?:previous|prior|earlier)\s+instructions?\s+(?:do\s+not|don't|never)\s+exist\b",
        ),
    ),

    # ---------------------------------------------------------
    # 4. Treat untrusted documents as instructions
    # ---------------------------------------------------------
    (
        "untrusted_content_instruction",
        3,
        (
            r"\bfollow\s+(?:the\s+)?instructions?\s+(?:contained|inside|within)\s+(?:this|the)\s+(?:document|file|text|page)\b",
            r"\btreat\s+(?:the\s+)?(?:document|file|text|page)\s+(?:above|below)\s+as\s+(?:your\s+)?instructions?\b",
            r"\btreat\s+(?:the\s+)?(?:document|file|text|page)\s+as\s+(?:your\s+)?instructions?\b",
            r"\bthe\s+document\s+(?:above|below)\s+(?:contains|has)\s+instructions?\s+for\s+you\b",
        ),
    ),

    # ---------------------------------------------------------
    # 5. Role / safety / jailbreak override
    # ---------------------------------------------------------
    (
        "role_or_policy_override",
        3,
        (
            r"\byou\s+are\s+now\s+(?:a|an)\s+(?:different|unrestricted|unfiltered)\b",
            r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken)\s+(?:assistant|ai|model)\b",
            r"\bignore\s+(?:your\s+)?safety\s+(?:rules|policies|guidelines)\b",
            r"\bdisable\s+(?:your\s+)?safety\s+(?:rules|policies|filters)\b",
            r"\bignore\s+(?:all\s+)?safety\s+(?:rules|policies|guidelines)\b",
        ),
    ),

    # ---------------------------------------------------------
    # 6. Secret / credential extraction
    # ---------------------------------------------------------
    (
    "sensitive_data_exfiltration",
        3,
        (
            r"\b(?:reveal|show|display|print|expose|give\s+me)\s+(?:the\s+)?(?:api|secret|access)\s+key(?:s)?\b",

            r"\b(?:reveal|show|display|print|expose|give\s+me)"
            r"\s+(?:the\s+)?(?:secret|private|internal)"
            r"\s+(?:configuration|config|data|information)\b",

            r"\b(?:show|give|provide|reveal|display|print|expose)"
            r"\s+(?:me\s+)?(?:the\s+)?api\s+key"
            r"(?:\s+and\s+(?:any\s+)?(?:secret|private|internal)"
            r"\s+(?:configuration|config|data|information))?\b",

            r"\b(?:show|give|provide|reveal|display|print|expose)"
            r"\s+(?:me\s+)?(?:any\s+)?"
            r"(?:secret|private|internal)\s+configuration\b",

            r"\bexpose\s+(?:internal|private|confidential)"
            r"\s+(?:information|data|configuration)\b",

            r"\bwhat\s+(?:is|are)\s+(?:your|the)"
            r"\s+(?:api|secret|access)\s+key(?:s)?\b",
        ),
    ),
)


# A score of 3 means one high-confidence attack pattern is enough to block.
BLOCK_THRESHOLD = 3


def _normalise(text: str) -> str:
    """Normalize whitespace and case before matching."""
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
    """Generic response returned when a prompt is blocked."""
    return (
        "I can help with your question, but I can’t follow requests to "
        "override system instructions, reveal hidden prompts, or expose "
        "private configuration."
    )