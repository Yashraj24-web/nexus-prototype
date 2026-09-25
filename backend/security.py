"""
Security Validator — blocks queries that attempt to access private data.

This is the gatekeeper between intent parsing and data access.
It validates structured intent AND raw query text for malicious patterns.
"""

import re

# Private field names that must never be queried
PRIVATE_FIELD_KEYWORDS = [
    "email", "e-mail", "mail",
    "phone", "mobile", "contact number", "phone number",
    "rsvp", "rsvps",
    "attendance", "attended",
    "password", "secret", "token", "api key",
    "private", "confidential", "internal",
]

# Prompt-injection / jailbreak patterns
INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above|all)\s+(instructions?|prompts?|rules?)",
    r"forget\s+(previous|prior|above|all|your)\s+(instructions?|prompts?|rules?)",
    r"override\s+(previous|prior|safety|security)",
    r"bypass\s+(security|filter|safety|rules?)",
    r"reveal\s+(private|hidden|secret|internal|all)",
    r"show\s+(me\s+)?(all|every|everyone'?s?)\s+(email|phone|password|private|secret|internal|rsvp|attendance)",
    r"give\s+(me\s+)?(all|every|everyone'?s?)\s+(email|phone|password|private|secret|internal|rsvp|attendance)",
    r"list\s+(all\s+)?(email|phone|password|private|secret|internal|rsvp|attendance)",
    r"dump\s+(all|the|every)",
    r"extract\s+(private|personal|sensitive)",
    r"act\s+as\s+(admin|root|superuser)",
    r"you\s+are\s+now\s+(admin|root|superuser|jailbroken)",
    r"system\s*prompt",
    r"\bDAN\b",
]


def validate_query(raw_query: str, intent: dict) -> dict:
    """
    Validate a query for security.

    Returns:
        {"allowed": True} or {"allowed": False, "reason": "..."}
    """
    q = raw_query.lower().strip()

    # Check for prompt-injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, q):
            return {
                "allowed": False,
                "reason": "Request blocked: Prompt-injection or jailbreak attempt detected.",
            }

    # Check for private field access in raw query
    for keyword in PRIVATE_FIELD_KEYWORDS:
        if keyword in q:
            return {
                "allowed": False,
                "reason": "Request attempts to access protected/private information.",
            }

    # If intent somehow requests private fields (defense in depth)
    # This shouldn't happen with our parser, but it's a safety net
    return {"allowed": True}
