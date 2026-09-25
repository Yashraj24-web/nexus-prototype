"""
NEXUS Security Engine 2.0 — AI-Native WAF & Security Validator
==============================================================

CORE SECURITY PRINCIPLE: "LLM != Database Access"

This module acts as the authoritative application security gatekeeper.
It analyzes natural-language and Hinglish queries BEFORE intent execution,
scores threats, enforces protected field policies, prevents prompt injection,
blocks SQL injection, detects privilege escalation, performs abuse rate limiting,
and maintains an immutable in-memory security audit log.
"""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict


# ── Threat Category Definitions ────────────────────────────────

class ThreatType:
    NONE = "NONE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    SENSITIVE_DATA_ACCESS = "SENSITIVE_DATA_ACCESS"
    SQL_INJECTION = "SQL_INJECTION"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    DATABASE_EXFILTRATION = "DATABASE_EXFILTRATION"
    ABUSE_RATE_LIMIT = "ABUSE_RATE_LIMIT"


# ── Protected Fields (Strict PII Policy) ───────────────────────
PROTECTED_FIELD_KEYWORDS = [
    # English
    "phone", "mobile", "contact number", "phone number", "phone numbers", "cell",
    "email", "e-mail", "mail address", "email id", "email ids", "email address", "emails",
    "password", "passwords", "passwd", "secret", "token", "tokens", "api key", "auth token",
    "rsvp", "rsvps", "attendance", "attendance record", "attendance records", "attended",
    "private message", "private messages", "dm", "dms", "chat history",
    "private channel", "private channels", "draft", "drafts",
    "organiser analytics", "organizer analytics", "admin analytics", "internal analytics",
    "ssn", "salary", "credit card", "bank",
    # Hinglish
    "phone no", "mobile number", "sabke phone", "sabke number", "sabki email",
    "private data", "secret data", "chupa hua data",
]

# ── Attack Detection Rules (English + Hinglish) ─────────────────

# 1. SQL Injection Patterns
SQL_INJECTION_PATTERNS = [
    r"(?i)\b(SELECT|DROP|INSERT|DELETE|UPDATE|ALTER|CREATE|EXEC|TRUNCATE)\b\s+.*\b(FROM|TABLE|INTO|DATABASE)\b",
    r"(?i)UNION\s+(ALL\s+)?SELECT",
    r"(?i)'.*OR.*['\d\s=]+--",
    r"(?i)'.*OR\s+'1'\s*=\s*'1",
    r"(?i)\bOR\s+1\s*=\s*1\b",
    r"(?i)--\s*$",
    r"(?i);\s*(DROP|SELECT|DELETE|INSERT|UPDATE)",
    r"(?i)give\s+me\s+the\s+sql\s+query\s+and\s+execute\s+it",
    r"(?i)execute\s+(raw\s+)?sql",
]

# 2. Privilege Escalation Patterns
PRIVILEGE_ESCALATION_PATTERNS = [
    r"(?i)act\s+as\s+(an?\s+)?(admin|administrator|root|superuser|system\s*operator)",
    r"(?i)pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(admin|administrator|root)",
    r"(?i)i\s+am\s+(the\s+)?(admin|administrator|root|superuser)",
    r"(?i)escalate\s+privilege",
    r"(?i)grant\s+(me\s+)?(admin|root)\s+access",
    r"(?i)bypass\s+permission\s+checks?",
    # Hinglish Privilege Escalation
    r"(?i)admin\s+ban\s*(ke|kar)\s*.*(data|dikhao|batao)",
    r"(?i)admin\s+access\s+do",
]

# 3. Prompt Injection & Jailbreak Patterns
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above|system|safety|security)\s*(instructions?|prompts?|rules?|directives?)",
    r"(?i)forget\s+(all\s+)?(your\s+|the\s+)?(previous|prior|above)?\s*(instructions?|prompts?|rules?|directives?)",
    r"(?i)override\s+(all\s+)?(previous|prior|safety|security|system)\s*(rules?|prompts?|checks?)?",
    r"(?i)bypass\s+(all\s+)?(security|filter|safety|rules?)",
    r"(?i)you\s+are\s+now\s+(a|an|in|jailbroken|unrestricted|god\s*mode|dan\s*mode)",
    r"(?i)disregard\s+(all\s+)?(previous|prior|rules?|instructions?)",
    r"(?i)system\s*prompt",
    r"\bDAN\s*mode\b",
    r"(?i)developer\s*mode\s*enabled",
    r"(?i)pretend\s+(there\s+are\s+no|you\s+have\s+no)\s+(rules|restrictions|limits)",
    # Hinglish Injection
    r"(?i)(previous|purane)\s+instructions?\s+(ignore|bhul)\s*(karo|jao)",
    r"(?i)security\s*(rules?)?\s*(bypass|override|hatao|todo)\s*karo",
    r"(?i)rules?\s*ignore\s*karo",
    r"(?i)instructions?\s*bhool\s*jao",
]

# 4. Database Exfiltration Patterns
EXFILTRATION_PATTERNS = [
    r"(?i)reveal\s+(the\s+)?(entire\s+)?(database|db|all\s+tables|schema)",
    r"(?i)dump\s+(the\s+)?(database|db|all\s+records|users?)",
    r"(?i)show\s+(me\s+)?(all\s+)?(database|db\s+records|raw\s+data)",
    r"(?i)extract\s+all\s+(data|users?|records)",
    # Hinglish
    r"(?i)poora\s+database\s+(dikhao|nikalo|dump\s*karo)",
    r"(?i)saara\s+data\s+(dikhao|batao)",
]


# ── In-Memory Security Audit Log ───────────────────────────────

MAX_AUDIT_LOGS = 500
SECURITY_AUDIT_LOGS: List[Dict[str, Any]] = []

# Rate limiting / abuse tracking: ip -> list of timestamps of suspicious requests
SUSPICIOUS_REQUEST_TRACKER = defaultdict(list)
ABUSE_WINDOW_SECONDS = 60
ABUSE_THRESHOLD_SUSPICIOUS = 4  # 4 suspicious requests within 60s triggers block


from blockchain import threat_ledger


def log_security_event(
    request_id: str,
    raw_query: str,
    risk_level: str,
    risk_score: int,
    threat_type: str,
    decision: str,
    reason: str,
    checks: Dict[str, str],
    client_ip: str = "127.0.0.1",
) -> Dict[str, Any]:
    """Records a safe security event in the audit log and mines it into the Blockchain Threat Ledger."""
    safe_snippet = (raw_query[:100] + "...") if len(raw_query) > 100 else raw_query
    
    event = {
        "id": f"sec-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "query_snippet": safe_snippet,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "threat_type": threat_type,
        "decision": decision,
        "reason": reason,
        "checks": checks,
        "client_ip": client_ip,
    }
    
    SECURITY_AUDIT_LOGS.insert(0, event)
    if len(SECURITY_AUDIT_LOGS) > MAX_AUDIT_LOGS:
        SECURITY_AUDIT_LOGS.pop()

    # Automatically anchor security decisions into the Blockchain Threat Ledger
    try:
        if decision == "BLOCKED" or threat_type != ThreatType.NONE:
            threat_ledger.add_security_block(threat_type, event)
    except Exception:
        pass
        
    return event


def get_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns the most recent security audit logs."""
    return SECURITY_AUDIT_LOGS[:limit]


def get_audit_stats() -> Dict[str, Any]:
    """Returns real aggregate security metrics computed from actual logs."""
    total = len(SECURITY_AUDIT_LOGS)
    allowed = sum(1 for log in SECURITY_AUDIT_LOGS if log["decision"] == "ALLOWED")
    blocked = sum(1 for log in SECURITY_AUDIT_LOGS if log["decision"] == "BLOCKED")
    critical = sum(1 for log in SECURITY_AUDIT_LOGS if log["risk_level"] == "CRITICAL")
    high = sum(1 for log in SECURITY_AUDIT_LOGS if log["risk_level"] == "HIGH")
    medium = sum(1 for log in SECURITY_AUDIT_LOGS if log["risk_level"] == "MEDIUM")
    low = sum(1 for log in SECURITY_AUDIT_LOGS if log["risk_level"] == "LOW")

    threat_counts = defaultdict(int)
    for log in SECURITY_AUDIT_LOGS:
        if log["threat_type"] != ThreatType.NONE:
            threat_counts[log["threat_type"]] += 1

    return {
        "total_requests": total,
        "allowed": allowed,
        "blocked": blocked,
        "risk_levels": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "most_common_threats": dict(threat_counts),
    }


# ── Core Security Analysis & Validation ────────────────────────

def analyze_and_validate(raw_query: str, intent: Optional[Dict[str, Any]] = None, client_ip: str = "127.0.0.1") -> Dict[str, Any]:
    """
    Comprehensive multi-layer security inspection.
    
    Returns structured security decision:
    {
      "allowed": bool,
      "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "risk_score": int (0-100),
      "threat_type": str,
      "reason": str,
      "action": "ALLOW" | "BLOCK",
      "checks": {
          "threat_scan": "PASSED" | "DETECTED",
          "permission_check": "VALIDATED" | "UNAUTHORIZED",
          "protected_fields": "SAFE" | "VIOLATION",
          "query_validation": "VALID" | "INVALID"
      },
      "request_id": str
    }
    """
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    q = (raw_query or "").strip()
    q_lower = q.lower()

    # Track requests for abuse detection
    now = time.time()
    recent_suspicious = [
        t for t in SUSPICIOUS_REQUEST_TRACKER[client_ip]
        if now - t < ABUSE_WINDOW_SECONDS
    ]
    SUSPICIOUS_REQUEST_TRACKER[client_ip] = recent_suspicious

    # Check 1: Abuse / Rate Limiting (Repeated suspicious requests)
    if len(recent_suspicious) >= ABUSE_THRESHOLD_SUSPICIOUS:
        decision = {
            "allowed": False,
            "risk_level": "CRITICAL",
            "risk_score": 95,
            "threat_type": ThreatType.ABUSE_RATE_LIMIT,
            "reason": "Temporary security block: Repeated suspicious attack requests detected from this session.",
            "action": "BLOCK",
            "checks": {
                "threat_scan": "DETECTED",
                "permission_check": "UNAUTHORIZED",
                "protected_fields": "SAFE",
                "query_validation": "INVALID",
            },
            "request_id": request_id,
        }
        log_security_event(request_id, q, "CRITICAL", 95, ThreatType.ABUSE_RATE_LIMIT, "BLOCKED", decision["reason"], decision["checks"], client_ip)
        return decision

    # Check 2: SQL Injection Detection (High priority)
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, q):
            SUSPICIOUS_REQUEST_TRACKER[client_ip].append(now)
            decision = {
                "allowed": False,
                "risk_level": "CRITICAL",
                "risk_score": 96,
                "threat_type": ThreatType.SQL_INJECTION,
                "reason": "SQL injection detected: Raw database manipulation queries are strictly prohibited.",
                "action": "BLOCK",
                "checks": {
                    "threat_scan": "DETECTED",
                    "permission_check": "UNAUTHORIZED",
                    "protected_fields": "SAFE",
                    "query_validation": "INVALID",
                },
                "request_id": request_id,
            }
            log_security_event(request_id, q, "CRITICAL", 96, ThreatType.SQL_INJECTION, "BLOCKED", decision["reason"], decision["checks"], client_ip)
            return decision

    # Check 3: Privilege Escalation
    for pattern in PRIVILEGE_ESCALATION_PATTERNS:
        if re.search(pattern, q):
            SUSPICIOUS_REQUEST_TRACKER[client_ip].append(now)
            decision = {
                "allowed": False,
                "risk_level": "HIGH",
                "risk_score": 82,
                "threat_type": ThreatType.PRIVILEGE_ESCALATION,
                "reason": "Privilege escalation attempt: Admin rights cannot be asserted through natural-language queries.",
                "action": "BLOCK",
                "checks": {
                    "threat_scan": "DETECTED",
                    "permission_check": "UNAUTHORIZED",
                    "protected_fields": "SAFE",
                    "query_validation": "INVALID",
                },
                "request_id": request_id,
            }
            log_security_event(request_id, q, "HIGH", 82, ThreatType.PRIVILEGE_ESCALATION, "BLOCKED", decision["reason"], decision["checks"], client_ip)
            return decision

    # Check 4: Prompt Injection / Instruction Overriding
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, q):
            SUSPICIOUS_REQUEST_TRACKER[client_ip].append(now)
            decision = {
                "allowed": False,
                "risk_level": "CRITICAL",
                "risk_score": 92,
                "threat_type": ThreatType.PROMPT_INJECTION,
                "reason": "Prompt-injection detected: Attempt to override system instructions or bypass security rules.",
                "action": "BLOCK",
                "checks": {
                    "threat_scan": "DETECTED",
                    "permission_check": "UNAUTHORIZED",
                    "protected_fields": "SAFE",
                    "query_validation": "INVALID",
                },
                "request_id": request_id,
            }
            log_security_event(request_id, q, "CRITICAL", 92, ThreatType.PROMPT_INJECTION, "BLOCKED", decision["reason"], decision["checks"], client_ip)
            return decision

    # Check 5: Database Exfiltration
    for pattern in EXFILTRATION_PATTERNS:
        if re.search(pattern, q):
            SUSPICIOUS_REQUEST_TRACKER[client_ip].append(now)
            decision = {
                "allowed": False,
                "risk_level": "CRITICAL",
                "risk_score": 90,
                "threat_type": ThreatType.DATABASE_EXFILTRATION,
                "reason": "Database exfiltration attempt: Bulk schema or database dumping is blocked.",
                "action": "BLOCK",
                "checks": {
                    "threat_scan": "DETECTED",
                    "permission_check": "UNAUTHORIZED",
                    "protected_fields": "SAFE",
                    "query_validation": "INVALID",
                },
                "request_id": request_id,
            }
            log_security_event(request_id, q, "CRITICAL", 90, ThreatType.DATABASE_EXFILTRATION, "BLOCKED", decision["reason"], decision["checks"], client_ip)
            return decision

    # Check 6: Sensitive PII / Protected Field Access
    for kw in PROTECTED_FIELD_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, q_lower) or kw in q_lower:
            SUSPICIOUS_REQUEST_TRACKER[client_ip].append(now)
            decision = {
                "allowed": False,
                "risk_level": "HIGH",
                "risk_score": 75,
                "threat_type": ThreatType.SENSITIVE_DATA_ACCESS,
                "reason": f"Access to protected field '{kw}' is restricted by privacy policy. Protected PII is never returned.",
                "action": "BLOCK",
                "checks": {
                    "threat_scan": "PASSED",
                    "permission_check": "UNAUTHORIZED",
                    "protected_fields": "VIOLATION",
                    "query_validation": "INVALID",
                },
                "request_id": request_id,
            }
            log_security_event(request_id, q, "HIGH", 75, ThreatType.SENSITIVE_DATA_ACCESS, "BLOCKED", decision["reason"], decision["checks"], client_ip)
            return decision

    # Check 7: Intent-Level Defense in Depth (Structured Intent Verification)
    if intent and isinstance(intent, dict):
        for k, v in intent.items():
            if str(k).lower() in ("email", "phone", "rsvp", "attendance", "password"):
                SUSPICIOUS_REQUEST_TRACKER[client_ip].append(now)
                decision = {
                    "allowed": False,
                    "risk_level": "HIGH",
                    "risk_score": 70,
                    "threat_type": ThreatType.SENSITIVE_DATA_ACCESS,
                    "reason": f"Structured intent extracted protected field '{k}'. Blocked by schema policy.",
                    "action": "BLOCK",
                    "checks": {
                        "threat_scan": "PASSED",
                        "permission_check": "UNAUTHORIZED",
                        "protected_fields": "VIOLATION",
                        "query_validation": "INVALID",
                    },
                    "request_id": request_id,
                }
                log_security_event(request_id, q, "HIGH", 70, ThreatType.SENSITIVE_DATA_ACCESS, "BLOCKED", decision["reason"], decision["checks"], client_ip)
                return decision

    # Query Passed All Security Checks: ALLOWED
    base_score = 5
    if len(q) > 80:
        base_score += 5

    decision = {
        "allowed": True,
        "risk_level": "LOW",
        "risk_score": base_score,
        "threat_type": ThreatType.NONE,
        "reason": "Query conforms to security and privacy policies. Public fields only.",
        "action": "ALLOW",
        "checks": {
            "threat_scan": "PASSED",
            "permission_check": "VALIDATED",
            "protected_fields": "SAFE",
            "query_validation": "VALID",
        },
        "request_id": request_id,
    }
    log_security_event(request_id, q, "LOW", base_score, ThreatType.NONE, "ALLOWED", decision["reason"], decision["checks"], client_ip)
    return decision


def validate_query(raw_query: str, intent: Optional[Dict[str, Any]] = None, client_ip: str = "127.0.0.1") -> Dict[str, Any]:
    """Backward compatibility wrapper returning the structured security decision."""
    return analyze_and_validate(raw_query, intent, client_ip)
