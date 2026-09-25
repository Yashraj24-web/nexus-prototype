"""
Search Engine — NEXUS Secure Search 2.0
========================================

CORE SECURITY PRINCIPLE: "LLM != Database Access"

This module receives ONLY validated structured intent.
It delegates query validation to `safe_query_builder`, which enforces:
- Explicit schema allowlist
- Server-side RBAC permissions
- Rejection of any unallowlisted or protected fields
- Output sanitization to guarantee NO private fields (email, phone, rsvp, attendance) ever leak.
"""

from typing import List, Dict, Any
from data import DEVELOPER_PROFILES, PUBLIC_FIELDS
from safe_query_builder import build_safe_query_plan, UserRole, QueryValidationError

# Scoring weights
SCORE_TECHNOLOGY = 40
SCORE_ROLE = 25
SCORE_LOCATION = 20
SCORE_RECENT = 15


def _sanitize_profile(profile: dict) -> dict:
    """Strictly strip private fields from a profile. Defense in depth."""
    return {k: v for k, v in profile.items() if k in PUBLIC_FIELDS}


def _compute_score(profile: dict, filters: dict) -> int:
    """Compute relevance score for a profile against safe, validated filters."""
    score = 0

    technology = filters.get("technology")
    role = filters.get("role")
    location = filters.get("location")
    recent = filters.get("recent", False)

    # Technology match — check skills list
    if technology:
        profile_skills = [s.lower() for s in profile.get("skills", [])]
        if technology.lower() in profile_skills:
            score += SCORE_TECHNOLOGY

    # Role match
    if role:
        profile_role = profile.get("role", "").lower()
        if role.lower() in profile_role:
            score += SCORE_ROLE

    # Location match
    if location:
        profile_city = profile.get("city", "").lower()
        if location.lower() == profile_city:
            score += SCORE_LOCATION

    # Recent activity bonus
    if recent:
        activity = profile.get("recent_activity", "").lower()
        recent_keywords = ["sept", "2026", "latest", "new"]
        if any(kw in activity for kw in recent_keywords):
            score += SCORE_RECENT

    return score


def search(intent: dict, user_role: UserRole = UserRole.PUBLIC_USER) -> list[dict]:
    """
    Search developer profiles using validated safe query plan.
    Enforces schema allowlists, server-side RBAC, and parameter sanitization.
    Returns ranked list of sanitized (public-only) profiles with scores.
    """
    # 1. Enforce Safe Query Plan via safe_query_builder
    try:
        query_plan = build_safe_query_plan(intent, user_role=user_role)
    except QueryValidationError as e:
        # Schema or policy violation
        return []

    filters = query_plan.filters
    results = []

    # 2. Match against database profiles
    # CRITICAL: Database content (like bios) is treated strictly as plain data/strings,
    # NEVER parsed as executable instructions!
    for profile in DEVELOPER_PROFILES:
        score = _compute_score(profile, filters)
        if score > 0:
            safe_profile = _sanitize_profile(profile)
            safe_profile["relevance_score"] = score
            results.append(safe_profile)

    # 3. Sort by relevance score descending
    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    # 4. Enforce limit from query plan
    return results[:query_plan.limit]
