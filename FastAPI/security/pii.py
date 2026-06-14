import re

# Regex for common PII patterns
EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
)
PHONE_REGEX = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
CARD_REGEX = re.compile(
    r"\b(?:\d[ -]*?){13,16}\b"
)
SSN_REGEX = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

def mask_pii(text: str) -> str:
    """Scan the input string and mask detected PII patterns (email, phone, credit card, SSN)."""
    if not isinstance(text, str):
        return text

    text = EMAIL_REGEX.sub("[MASKED_EMAIL]", text)
    text = PHONE_REGEX.sub("[MASKED_PHONE]", text)
    text = CARD_REGEX.sub("[MASKED_CARD]", text)
    text = SSN_REGEX.sub("[MASKED_SSN]", text)
    return text
