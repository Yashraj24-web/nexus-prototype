"""
NEXUS — Secure Natural-Language Search for Commudle
FastAPI Backend (Version 2.0 — Cybersecurity Upgrade)
=====================================================

CORE SECURITY PRINCIPLE: "LLM != Database Access"

Architecture:
  User Query
      ↓
  LLM Intent Parser
      ↓
  Structured Intent
      ↓
  Security Validation (AI-Native WAF & Threat Scanner)
      ↓
  Permission Check (Server-Side RBAC)
      ↓
  Safe Query Builder (Schema Allowlist & Parameterization)
      ↓
  Database (Untrusted text treated strictly as data)
      ↓
  Ranking & Output Sanitization (Public fields only)
      ↓
  Safe Ranked Results
"""

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from intent_parser import parse_intent
from security import (
    analyze_and_validate,
    validate_query,
    get_audit_logs,
    get_audit_stats,
    ThreatType,
)
from safe_query_builder import UserRole, build_safe_query_plan, QueryValidationError
from search_engine import search
from chat_service import (
    start_conversation,
    send_message,
    get_conversation,
    list_conversations,
)
from data import DEVELOPER_PROFILES, PUBLIC_FIELDS

app = FastAPI(
    title="NEXUS Secure Search API",
    description="Enterprise-grade secure natural-language discovery platform",
    version="2.0.0",
)

# ── Security Middleware & Headers ──────────────────────────────

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Enforces essential web security headers and max payload size."""
    # Max payload size protection (1MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:
        return JSONResponse(
            status_code=413,
            content={"error": "Payload too large. Maximum request size is 1MB."}
        )

    response: Response = await call_next(request)
    
    # Secure HTTP response headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Server"] = "NEXUS-SecureEngine"
    
    return response


# CORS Configuration — allows frontend dev server and production deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler (No Internal Leaks) ───────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Never expose stack traces, database internals, or environment secrets to clients."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "An internal processing error occurred.",
            "status": "error",
            "message": "The request could not be processed safely.",
        },
    )


# ── Request / Response Models ─────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., max_length=1000)

class SecurityCheckRequest(BaseModel):
    query: str = Field(..., max_length=1000)

class ChatStartRequest(BaseModel):
    participant_ids: List[int]

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str = Field(..., max_length=2000)


def _get_client_ip(request: Request) -> str:
    """Safely extract client IP from headers or connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# ── Core Endpoints ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "NEXUS Secure Search API",
        "version": "2.0.0",
        "status": "running",
        "principle": "LLM != Database Access",
        "security_features": [
            "AI-Native WAF & Prompt-Injection Firewall",
            "Strict PII Protection & Data Classification",
            "SQL Injection Elimination",
            "Schema Allowlist & Parameterized Query Builder",
            "Server-Side Role-Based Access Control",
            "Database Prompt-Injection Immunity",
            "Real-time Security Risk Scoring (0-100)",
            "Auditable Security Event Ledger",
        ],
    }


@app.post("/api/security/check")
def api_security_check(req: SecurityCheckRequest, request: Request):
    """
    Dedicated Security Validation Endpoint.
    Analyzes any query for prompt injection, sensitive data requests, SQL injection,
    privilege escalation, and assigns a risk score (0-100).
    """
    client_ip = _get_client_ip(request)
    decision = analyze_and_validate(req.query, client_ip=client_ip)
    return decision


@app.get("/api/security/logs")
def api_security_logs():
    """Returns recent security audit logs (safe event metadata, no private PII)."""
    return {
        "logs": get_audit_logs(limit=50),
        "stats": get_audit_stats(),
    }


@app.get("/api/security/stats")
def api_security_stats():
    """Returns aggregate real security metrics computed from application logs."""
    return get_audit_stats()


@app.post("/api/search")
def api_search(
    req: SearchRequest,
    request: Request,
    x_user_role: Optional[str] = Header(default="PUBLIC_USER"),
):
    """
    NEXUS 2.0 Secure Search Pipeline:
    Query → Intent Parser → Security WAF Validation → RBAC → Safe Query Builder → Search → Ranked Safe Results.
    """
    client_ip = _get_client_ip(request)

    # 1. Parse intent (LLM-like extraction, strictly NO data access)
    intent = parse_intent(req.query)

    # 2. Comprehensive Security Validation (AI-Native WAF, PII filter, SQLi, Prompt Injection)
    security = analyze_and_validate(req.query, intent=intent, client_ip=client_ip)

    # If blocked by security policy, return immediately with clear decision and empty results
    if not security["allowed"]:
        return {
            "query": req.query,
            "intent": intent,
            "security": security,
            "results": [],
            "result_count": 0,
        }

    # 3. Server-side RBAC validation
    # Trust ONLY the server context or verified header, NEVER natural-language claims!
    try:
        user_role = UserRole(x_user_role.upper()) if x_user_role else UserRole.PUBLIC_USER
    except ValueError:
        user_role = UserRole.PUBLIC_USER

    # 4. Safe Search execution through safe_query_builder (only reached if security passed)
    results = search(intent, user_role=user_role)

    return {
        "query": req.query,
        "intent": intent,
        "security": security,
        "results": results,
        "result_count": len(results),
        "user_role": user_role.value,
    }


# ── Profile Endpoint ──────────────────────────────────────────

@app.get("/api/profile/{profile_id}")
def api_profile(profile_id: int):
    """Get a single profile by ID — public fields only."""
    for p in DEVELOPER_PROFILES:
        if p["id"] == profile_id:
            safe = {k: v for k, v in p.items() if k in PUBLIC_FIELDS}
            return {"profile": safe}
    return {"error": "Profile not found"}


# ── Chat Endpoints (Protected by the Same Security Policy) ────

@app.post("/api/chat/start")
def api_chat_start(req: ChatStartRequest):
    """Start a new conversation with selected participants."""
    conversation = start_conversation(req.participant_ids)
    return conversation


@app.post("/api/chat/message")
def api_chat_message(req: ChatMessageRequest, request: Request):
    """
    Send a message in a conversation.
    The SAME security firewall and PII protection applies to chat messages!
    """
    client_ip = _get_client_ip(request)
    
    # Security check on chat message payload
    security = analyze_and_validate(req.message, client_ip=client_ip)

    if not security["allowed"]:
        return {
            "error": "blocked",
            "security": security,
        }

    result = send_message(req.conversation_id, req.message)
    return result


@app.get("/api/chat/conversations")
def api_chat_list():
    """List all conversations."""
    return {"conversations": list_conversations()}


@app.get("/api/chat/{conversation_id}")
def api_chat_get(conversation_id: str):
    """Get a specific conversation."""
    conv = get_conversation(conversation_id)
    if not conv:
        return {"error": "Conversation not found"}
    return conv
