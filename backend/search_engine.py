"""
Search Engine — finds and ranks developer profiles based on structured intent.

This module ONLY receives validated, structured intent.
It NEVER processes raw user queries directly.
It NEVER returns private fields.
"""

from data import DEVELOPER_PROFILES, PUBLIC_FIELDS

# Scoring weights
SCORE_TECHNOLOGY = 40
SCORE_ROLE = 25
SCORE_LOCATION = 20
SCORE_RECENT = 15


def _sanitize_profile(profile: dict) -> dict:
    """Strip private fields from a profile. Defense in depth."""
    return {k: v for k, v in profile.items() if k in PUBLIC_FIELDS}


def _compute_score(profile: dict, intent: dict) -> int:
    """Compute relevance score for a profile against the intent."""
    score = 0

    technology = intent.get("technology")
    role = intent.get("role")
    location = intent.get("location")
    recent = intent.get("recent", False)

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


def search(intent: dict) -> list[dict]:
    """
    Search developer profiles using validated structured intent.
    Returns ranked list of sanitized (public-only) profiles with scores.
    """
    results = []

    for profile in DEVELOPER_PROFILES:
        score = _compute_score(profile, intent)
        if score > 0:
            safe_profile = _sanitize_profile(profile)
            safe_profile["relevance_score"] = score
            results.append(safe_profile)

    # Sort by score descending
    results.sort(key=lambda x: x["relevance_score"], reverse=True)

    return results
