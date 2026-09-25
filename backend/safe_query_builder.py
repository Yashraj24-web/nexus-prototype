"""
Safe Query Builder — NEXUS Secure Search 2.0
============================================

CORE SECURITY PRINCIPLE: "LLM != Database Access"

The LLM is an intent interpreter, NOT a database query engine.
This component sits strictly between validated structured intent and data access.

Responsibilities:
1. Accept ONLY validated structured intent
2. Enforce explicit ALLOWED_SEARCH_FIELDS allowlist
3. Reject any fields in PROTECTED_FIELDS
4. Enforce server-side Role-Based Access Control (RBAC)
5. Build parameter-safe query filters (prevent any raw SQL or arbitrary execution)
6. Reject dangerous operators or unallowlisted structures
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class UserRole(str, Enum):
    PUBLIC_USER = "PUBLIC_USER"
    ORGANIZER = "ORGANIZER"
    ADMIN = "ADMIN"


# Explicit allowlist of searchable fields
ALLOWED_SEARCH_FIELDS = {
    "name",
    "role",
    "skills",
    "city",
    "location",  # synonym mapped to city
    "bio",
    "recent_activity",
    "technology",
    "content_type",
    "recent",
}

# Protected fields that must NEVER be searched or returned in discovery
PROTECTED_FIELDS = {
    "email",
    "phone",
    "password",
    "private_message",
    "private_messages",
    "rsvp",
    "attendance",
    "private_channel",
    "private_channels",
    "draft",
    "drafts",
    "organiser_analytics",
    "internal_id",
    "secret",
    "token",
}

# Server-side RBAC Permission Matrix
ROLE_PERMISSIONS = {
    UserRole.PUBLIC_USER: {
        "can_search_public": True,
        "can_access_protected": False,
        "can_access_analytics": False,
        "max_results": 20,
    },
    UserRole.ORGANIZER: {
        "can_search_public": True,
        "can_access_protected": False,
        "can_access_analytics": True,
        "max_results": 50,
    },
    UserRole.ADMIN: {
        "can_search_public": True,
        "can_access_protected": False,  # Admins use dedicated audit tools, not discovery search
        "can_access_analytics": True,
        "can_view_audit_logs": True,
        "max_results": 100,
    },
}


class QueryValidationError(Exception):
    """Raised when query intent violates schema or security policies."""
    pass


class SafeQueryPlan:
    """Represents a validated, parameterized search plan ready for safe execution."""
    def __init__(self, filters: Dict[str, Any], role: UserRole, limit: int):
        self.filters = filters
        self.role = role
        self.limit = limit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filters": self.filters,
            "role": self.role.value,
            "limit": self.limit,
            "schema_verified": True,
        }


def build_safe_query_plan(intent: Dict[str, Any], user_role: UserRole = UserRole.PUBLIC_USER) -> SafeQueryPlan:
    """
    Validates structured intent against allowlists, RBAC, and parameter policies.
    Returns a SafeQueryPlan or raises QueryValidationError.

    NEVER generates or accepts raw SQL.
    """
    if not isinstance(intent, dict):
        raise QueryValidationError("Intent must be a structured dictionary.")

    # 1. Verify user role permissions
    permissions = ROLE_PERMISSIONS.get(user_role)
    if not permissions or not permissions.get("can_search_public"):
        raise QueryValidationError(f"Role '{user_role}' is not authorized to search.")

    validated_filters = {}

    # 2. Check every field against ALLOWED and PROTECTED lists
    for key, value in intent.items():
        key_lower = str(key).lower().strip()

        # Reject protected fields immediately
        if key_lower in PROTECTED_FIELDS:
            raise QueryValidationError(
                f"Field '{key}' is a protected field and cannot be queried."
            )

        # Skip metadata keys not part of query filtering
        if key_lower in ("raw_query", "content_type"):
            continue

        # Reject fields outside schema allowlist
        if key_lower not in ALLOWED_SEARCH_FIELDS:
            raise QueryValidationError(
                f"Field '{key}' is not in the allowed search schema."
            )

        # Validate value: must be safe primitive types (str, bool, int, list of str)
        if value is None:
            continue

        if isinstance(value, str):
            # Sanitize control characters
            clean_val = value.replace("\x00", "").strip()
            # Reject SQL keywords inside filter values
            upper_val = clean_val.upper()
            dangerous_sql = ["DROP TABLE", "DELETE FROM", "UNION SELECT", "SELECT *", "--", ";"]
            if any(sq in upper_val for sq in dangerous_sql):
                raise QueryValidationError(f"Dangerous SQL pattern detected in filter '{key}'.")
            
            # Map location to city if needed
            if key_lower == "location":
                validated_filters["location"] = clean_val
                validated_filters["city"] = clean_val
            else:
                validated_filters[key_lower] = clean_val

        elif isinstance(value, bool):
            validated_filters[key_lower] = value
        elif isinstance(value, int):
            validated_filters[key_lower] = value
        elif isinstance(value, list) and all(isinstance(x, str) for x in value):
            validated_filters[key_lower] = [x.replace("\x00", "").strip() for x in value]
        else:
            raise QueryValidationError(f"Unsupported data type for filter field '{key}'.")

    limit = permissions.get("max_results", 20)
    return SafeQueryPlan(filters=validated_filters, role=user_role, limit=limit)
