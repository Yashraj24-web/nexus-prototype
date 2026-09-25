"""
NEXUS — Secure Natural-Language Search for Commudle
FastAPI Backend (Prototype)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from intent_parser import parse_intent
from security import validate_query
from search_engine import search
from chat_service import start_conversation, send_message, get_conversation, list_conversations
from data import DEVELOPER_PROFILES, PUBLIC_FIELDS

app = FastAPI(
    title="NEXUS Search API",
    description="Secure natural-language search prototype for Commudle",
    version="0.2.0",
)

# Allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str

class ChatStartRequest(BaseModel):
    participant_ids: list[int]

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str


# ── Existing Endpoints ────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "NEXUS Search API", "status": "running", "version": "0.2.0"}


@app.post("/api/search")
def api_search(req: SearchRequest):
    # Step 1 — Parse intent (LLM-like extraction, no data access)
    intent = parse_intent(req.query)

    # Step 2 — Security validation
    security = validate_query(req.query, intent)

    if not security["allowed"]:
        return {
            "query": req.query,
            "intent": intent,
            "security": security,
            "results": [],
            "result_count": 0,
        }

    # Step 3 — Safe search (only reached if security passes)
    results = search(intent)

    return {
        "query": req.query,
        "intent": intent,
        "security": {"allowed": True},
        "results": results,
        "result_count": len(results),
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


# ── Chat Endpoints ────────────────────────────────────────────

@app.post("/api/chat/start")
def api_chat_start(req: ChatStartRequest):
    """Start a new conversation with selected participants."""
    conversation = start_conversation(req.participant_ids)
    return conversation


@app.post("/api/chat/message")
def api_chat_message(req: ChatMessageRequest):
    """Send a message in a conversation.
    Security validation is applied to chat messages too."""
    # Security check on chat messages
    intent = parse_intent(req.message)
    security = validate_query(req.message, intent)

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
