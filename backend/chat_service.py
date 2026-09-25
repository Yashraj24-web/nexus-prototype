"""
Chat Service — in-memory mock chat for NEXUS prototype.
All conversations are synthetic demo data.
No real messaging system is connected.
"""

import uuid
from datetime import datetime, timezone
from data import DEVELOPER_PROFILES, PUBLIC_FIELDS

# In-memory store
_conversations = {}

# Synthetic auto-reply messages per person (keyed by profile id)
_AUTO_REPLIES = {
    1: ["Hey! Great to connect. I've been working on some Jetpack Compose projects lately.", "Would love to collaborate on an Android project!"],
    2: ["Hi there! Always happy to chat about Flutter and Dart.", "Let me know if you need help with cross-platform development."],
    3: ["Hello! I'm currently deep into FastAPI and PostgreSQL.", "Happy to discuss backend architecture anytime."],
    4: ["Hey! Full-stack dev here. React + Node.js is my jam.", "Let's build something together!"],
    5: ["Hi! I've got extensive Android experience with Java and Kotlin.", "Currently working on open-source tools."],
    6: ["Hello! I'm passionate about ML and NLP.", "Let me know if you want to discuss LLM security."],
    7: ["Hey! Flutter enthusiast here.", "I've been contributing to some open-source Flutter plugins."],
    8: ["Hi! DevOps is my world — Docker, K8s, CI/CD.", "Happy to help with deployment strategies."],
    9: ["Hey! Android dev from Lucknow here.", "Just won the Lucknow Hackathon, feeling great!"],
    10: ["Hi! I love designing intuitive UIs.", "Let's talk about design systems and user experience."],
}


def _get_safe_participant(profile_id: int) -> dict | None:
    """Get public-only participant info by id."""
    for p in DEVELOPER_PROFILES:
        if p["id"] == profile_id:
            return {k: v for k, v in p.items() if k in PUBLIC_FIELDS}
    return None


def start_conversation(participant_ids: list[int]) -> dict:
    """Start a new conversation with the given participant IDs."""
    conv_id = f"demo-conv-{uuid.uuid4().hex[:8]}"
    participants = []
    for pid in participant_ids:
        p = _get_safe_participant(pid)
        if p:
            participants.append(p)

    now = datetime.now(timezone.utc).isoformat()

    # Generate welcome messages from participants
    messages = []
    for p in participants:
        pid = p["id"]
        replies = _AUTO_REPLIES.get(pid, ["Hello!"])
        messages.append({
            "id": uuid.uuid4().hex[:8],
            "sender_id": pid,
            "sender_name": p["name"],
            "content": replies[0],
            "timestamp": now,
        })

    conversation = {
        "conversation_id": conv_id,
        "participants": participants,
        "messages": messages,
        "created_at": now,
    }
    _conversations[conv_id] = conversation
    return conversation


def send_message(conversation_id: str, message: str, sender_name: str = "You") -> dict:
    """Send a message in a conversation and get synthetic replies."""
    conv = _conversations.get(conversation_id)
    if not conv:
        return {"error": "Conversation not found"}

    now = datetime.now(timezone.utc).isoformat()

    # Add user message
    user_msg = {
        "id": uuid.uuid4().hex[:8],
        "sender_id": 0,
        "sender_name": sender_name,
        "content": message,
        "timestamp": now,
    }
    conv["messages"].append(user_msg)

    # Generate one synthetic reply from a random participant
    import random
    participant = random.choice(conv["participants"])
    pid = participant["id"]
    replies = _AUTO_REPLIES.get(pid, ["Thanks for reaching out!"])
    reply_text = random.choice(replies)

    reply_msg = {
        "id": uuid.uuid4().hex[:8],
        "sender_id": pid,
        "sender_name": participant["name"],
        "content": reply_text,
        "timestamp": now,
    }
    conv["messages"].append(reply_msg)

    return {
        "user_message": user_msg,
        "reply": reply_msg,
        "conversation_id": conversation_id,
    }


def get_conversation(conversation_id: str) -> dict | None:
    """Get a conversation by ID."""
    return _conversations.get(conversation_id)


def list_conversations() -> list[dict]:
    """List all conversations (summary only)."""
    result = []
    for conv in _conversations.values():
        last_msg = conv["messages"][-1] if conv["messages"] else None
        result.append({
            "conversation_id": conv["conversation_id"],
            "participants": [{"id": p["id"], "name": p["name"], "role": p["role"]} for p in conv["participants"]],
            "last_message": last_msg,
            "created_at": conv["created_at"],
            "message_count": len(conv["messages"]),
        })
    return result
