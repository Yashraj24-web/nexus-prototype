"""
Intent Parser — converts natural-language queries into structured intent.

IMPORTANT SECURITY RULE:
This module NEVER touches the database/data store.
It ONLY produces structured JSON intent from query text.
"""

import re

# Known technology keywords
TECHNOLOGIES = [
    "android", "flutter", "dart", "kotlin", "java", "react", "node",
    "python", "fastapi", "django", "typescript", "javascript",
    "tensorflow", "docker", "kubernetes", "firebase", "aws",
    "mongodb", "postgresql", "figma", "css", "html",
    "jetpack", "compose", "nlp", "llm", "ml",
]

# Known roles
ROLES = [
    "developer", "engineer", "designer", "devops", "ml engineer",
    "full-stack", "fullstack", "frontend", "backend", "mobile",
]

# Known cities
CITIES = [
    "lucknow", "delhi", "bangalore", "bengaluru", "mumbai",
    "hyderabad", "pune", "chennai", "kolkata", "jaipur",
]

# Hinglish mappings
HINGLISH_MAP = {
    "mujhe": "",
    "chahiye": "",
    "mein": "in",
    "wale": "",
    "dikhao": "show",
    "batao": "tell",
    "dhundho": "find",
    "karo": "",
    "ke": "",
    "ka": "",
    "ki": "",
    "hai": "",
    "hain": "",
    "jo": "who",
    "aur": "and",
    "ya": "or",
    "sab": "all",
    "sabhi": "all",
    "naye": "recent",
    "purane": "old",
}

RECENT_KEYWORDS = ["recent", "latest", "new", "active", "naye"]


def parse_intent(query: str) -> dict:
    """
    Parse a natural-language query into structured intent.
    Supports English and basic Hinglish.
    """
    q = query.lower().strip()

    # Normalize Hinglish tokens
    tokens = q.split()
    normalized_tokens = []
    for token in tokens:
        mapped = HINGLISH_MAP.get(token)
        if mapped is not None:
            if mapped:  # non-empty mapping
                normalized_tokens.append(mapped)
        else:
            normalized_tokens.append(token)
    normalized = " ".join(normalized_tokens)

    # Extract technology
    technology = None
    for tech in TECHNOLOGIES:
        if tech in normalized:
            technology = tech.capitalize()
            # Special casing
            tech_upper_map = {
                "Fastapi": "FastAPI",
                "Aws": "AWS",
                "Css": "CSS",
                "Html": "HTML",
                "Nlp": "NLP",
                "Llm": "LLM",
                "Ml": "ML",
                "Mongodb": "MongoDB",
                "Postgresql": "PostgreSQL",
                "Nodejs": "Node.js",
                "Node": "Node.js",
            }
            technology = tech_upper_map.get(technology, technology)
            break

    # Extract role
    role = None
    for r in ROLES:
        if r in normalized:
            role = r.title()
            break
    # Default to "Developer" if technology found but no explicit role
    if technology and not role:
        role = "Developer"

    # Extract city
    location = None
    for city in CITIES:
        if city in normalized:
            location = city.capitalize()
            if location == "Bengaluru":
                location = "Bangalore"
            break

    # Check for recency
    recent = any(kw in normalized for kw in RECENT_KEYWORDS)

    return {
        "content_type": "person",
        "technology": technology,
        "role": role,
        "location": location,
        "recent": recent,
        "raw_query": query,
    }
