"""
PII Masking and Redaction Utilities for IntelliSupply.

Provides functions to redact customer names, phone numbers, emails, and addresses
from both unstructured text and structured dictionary payloads.
"""

from __future__ import annotations

import re
from typing import Any

# Compile regular expressions for efficiency
EMAIL_REGEX = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
)

# Standard phone number pattern (matches 10-digit numbers, with optional international prefix)
PHONE_REGEX = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?(\d{2})\d{6}(\d{2})\)?\b"
)

# US/India Zip/Pin Code pattern
ZIP_REGEX = re.compile(
    r"\b\d{5}(?:-\d{4})?\b|\b\d{6}\b"
)

# Address keywords pattern to help identify and redact address strings in text
ADDRESS_KEYWORDS_REGEX = re.compile(
    r"(?i)\b\d+\s+([a-z0-9\s,.-]+(street|st|avenue|ave|road|rd|way|drive|dr|boulevard|blvd|lane|ln|apt|apartment|suite|ste|pincode|zip|flat|building))\b"
)

# Name pattern regex (capitalized word sequences that are likely names)
# Skips single words to prevent false positives for start of sentences
NAME_PATTERN_REGEX = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)


class PIIMasker:
    """Configurable utility for PII masking/redaction on text and structured data."""

    def __init__(
        self,
        mask_names: bool = True,
        mask_phones: bool = True,
        mask_emails: bool = True,
        mask_addresses: bool = True,
    ):
        self.mask_names = mask_names
        self.mask_phones = mask_phones
        self.mask_emails = mask_emails
        self.mask_addresses = mask_addresses

    def mask_text(self, text: str) -> str:
        """
        Scan unstructured text and redact any PII using regex patterns.
        
        Examples:
            "Call Rahul Sharma at 9876543210" -> "Call [REDACTED] at 98XXXXXX10"
        """
        if not text or not isinstance(text, str):
            return text

        masked = text

        # 1. Mask Emails
        if self.mask_emails:
            masked = EMAIL_REGEX.sub("[EMAIL_REDACTED]", masked)

        # 2. Mask Phone Numbers (replace middle 6 digits with X, keep first 2 and last 2)
        if self.mask_phones:
            # We match the prefix optionally, but the core 10 digits gets captured
            # format: 98XXXXXX10
            def phone_sub(match: re.Match) -> str:
                # Get the full matched string
                full_match = match.group(0)
                # Filter out non-digits to find the core 10 digits
                digits = "".join(c for c in full_match if c.isdigit())
                if len(digits) >= 10:
                    # Keep first 2 and last 2 digits of the phone number, pad the rest
                    start = digits[:2]
                    end = digits[-2:]
                    return f"{start}XXXXXX{end}"
                return "[PHONE_REDACTED]"

            masked = PHONE_REGEX.sub(phone_sub, masked)

        # 3. Mask Addresses (Zip code & Address strings)
        if self.mask_addresses:
            masked = ADDRESS_KEYWORDS_REGEX.sub("[ADDRESS_REDACTED]", masked)
            masked = ZIP_REGEX.sub("[ZIP_REDACTED]", masked)

        # 4. Mask Customer Names
        if self.mask_names:
            # Replaces pairs of capitalized words (proper names)
            # To minimize false positives, we ignore common words or check contexts.
            # Here we replace any double-capitalized proper names.
            # A whitelist can be added to skip months (e.g. "January First") or common terms.
            exclude_words = {"January", "February", "March", "April", "May", "June", 
                             "July", "August", "September", "October", "November", "December",
                             "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
            
            def name_sub(match: re.Match) -> str:
                name = match.group(1)
                # Check if any component is a weekday/month
                if any(part in exclude_words for part in name.split()):
                    return name
                return "[REDACTED]"
            
            masked = NAME_PATTERN_REGEX.sub(name_sub, masked)

        return masked

    def mask_data(self, data: Any) -> Any:
        """
        Recursively traverse dictionaries and lists to mask PII in key-value pairs
        as well as string values.
        """
        if isinstance(data, dict):
            masked_dict = {}
            for k, v in data.items():
                k_lower = str(k).lower()
                # Direct check for sensitive keys
                if k_lower in ("customer_name", "recipient_name", "name") and isinstance(v, str):
                    masked_dict[k] = "[REDACTED]"
                elif k_lower in ("phone", "phone_number", "mobile") and isinstance(v, str):
                    # Mask phone numbers (e.g. 9876543210 -> 98XXXXXX10)
                    digits = "".join(c for c in v if c.isdigit())
                    if len(digits) >= 10:
                        masked_dict[k] = f"{digits[:2]}XXXXXX{digits[-2:]}"
                    else:
                        masked_dict[k] = "[PHONE_REDACTED]"
                elif k_lower in ("email", "email_address") and isinstance(v, str):
                    masked_dict[k] = "[EMAIL_REDACTED]"
                elif k_lower in ("address", "street", "location_address") and isinstance(v, str):
                    masked_dict[k] = "[ADDRESS_REDACTED]"
                else:
                    # Recurse for nested values
                    masked_dict[k] = self.mask_data(v)
            return masked_dict

        elif isinstance(data, list):
            return [self.mask_data(item) for item in data]

        elif isinstance(data, str):
            # Apply text-based masking rules to the string itself
            return self.mask_text(data)

        return data


# Default instance for quick imports
default_masker = PIIMasker()
