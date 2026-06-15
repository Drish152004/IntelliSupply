import re

# Regex patterns for prompt injection attempts and dangerous database manipulation commands
INJECTION_PATTERNS = [
    # System instruction bypasses / Jailbreak patterns
    re.compile(r"\bignore\s+(?:all\s+)?previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+a\s+helpful\b", re.IGNORECASE),
    re.compile(r"\bignore\s+above\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+warn\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+override\b", re.IGNORECASE),
    # Dangerous SQL/Cypher database command combinations (stacked query prevention)
    re.compile(r";\s*(?:DROP|DELETE|TRUNCATE|ALTER|UPDATE|INSERT)\b", re.IGNORECASE),
    re.compile(r"\bUNION\s+SELECT\b", re.IGNORECASE),
    re.compile(r"\bOR\s+1\s*=\s*1\b", re.IGNORECASE),
]

def check_prompt_injection(text: str) -> bool:
    """Return True if a prompt injection or unsafe SQL/Cypher query command is detected."""
    if not isinstance(text, str):
        return False

    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False
