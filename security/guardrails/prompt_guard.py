"""
Prompt Injection Guardrails for IntelliSupply.

Protects against common injection attacks, including instructions override,
secrets exposure, database dump attempts, and jailbreaks.
"""

from __future__ import annotations

import re
from typing import Tuple

# Define regex patterns for typical prompt injection strategies
INJECTION_PATTERNS = [
    # 1. Instruction overrides
    (
        re.compile(
            r"(?i)\b(ignore|bypass|override|forget|reset|delete)\b.*\b(previous|system|instructions?|rules?|safety|restrictions?|directives?)\b"
        ),
        "Instruction override pattern detected."
    ),
    (
        re.compile(r"(?i)\byou\s+are\s+now\s+a\b|\byou\s+must\s+act\s+as\b"),
        "Role-play hijacking pattern detected."
    ),
    # 2. Secret exposure
    (
        re.compile(
            r"(?i)\b(reveal|show|expose|print|output|dump|tell)\b.*\b(system\s+prompt|prompts?|instructions?|secrets?|api_keys?|passwords?|credentials?|rules?)\b"
        ),
        "Secret leakage request detected."
    ),
    # 3. Database dumps (SQL injection attempt or direct command)
    (
        re.compile(
            r"(?i)\b(dump\s+database|database\s+dump|show\s+tables|show\s+databases)\b|\bselect\b.*\bfrom\b"
        ),
        "Database dump or SQL query attempt detected."
    ),
    # 4. System prompt access
    (
        re.compile(r"(?i)\bsystem\s+prompt\b|\bdeveloper\s+mode\b|\bjailbreak\b"),
        "Jailbreak or system prompt extraction attempt detected."
    ),
    # 5. General bypass patterns
    (
        re.compile(
            r"(?i)\bbypass\b.*\b(restrictions?|safety|filters?|boundaries|limits?)\b"
        ),
        "Bypass restrictions attempt detected."
    ),
]


def check_prompt_injection(prompt: str) -> Tuple[bool, str | None]:
    """
    Check if a prompt contains prompt injection attempts.
    
    Returns:
        (is_safe, error_message)
        - is_safe (bool): True if the prompt is deemed safe, False if injection is detected.
        - error_message (str | None): A generic user-safe error message if unsafe, else None.
    """
    if not prompt or not isinstance(prompt, str):
        return True, None

    for pattern, description in INJECTION_PATTERNS:
        if pattern.search(prompt):
            # We import logger locally to prevent circular import issues
            from security.audit.logger import log_security_violation
            
            # Log the security violation with details
            log_security_violation(
                violation_type="PROMPT_INJECTION",
                details=f"Query failed guardrails check. Pattern matched: {description}. Query snippet: {prompt[:100]}..."
            )
            
            return False, "Security Alert: Input query rejected due to safety policy violation."

    return True, None
