"""Storage for conversations - now using SQLite database."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR, USE_SQLITE_DB

# Import both JSON and SQLite backends
if USE_SQLITE_DB:
    from .database import (
        create_conversation_db,
        get_conversation_db,
        list_conversations_db,
        add_user_message_db,
        add_assistant_message_db,
        update_conversation_title_db,
    )


def ensure_data_dir():
    """Ensure the data directory exists."""
    if not USE_SQLITE_DB:
        Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation (JSON backend only)."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    if USE_SQLITE_DB:
        return create_conversation_db(conversation_id)
    
    # JSON backend (legacy)
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": []
    }

    # Save to file
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    if USE_SQLITE_DB:
        return get_conversation_db(conversation_id)
    
    # JSON backend (legacy)
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage (JSON backend only).

    Args:
        conversation: Conversation dict to save
    """
    if USE_SQLITE_DB:
        # Not needed for SQLite - data is saved via direct DB operations
        return
    
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    if USE_SQLITE_DB:
        return list_conversations_db()
    
    # JSON backend (legacy)
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                # Return metadata only
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "message_count": len(data["messages"])
                })

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    if USE_SQLITE_DB:
        add_user_message_db(conversation_id, content)
        return
    
    # JSON backend (legacy)
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    fact_check: List[Dict[str, Any]],
    stage3: List[Dict[str, Any]],
    stage4: Dict[str, Any]
):
    """
    Add an assistant message with all 4 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        fact_check: List of fact-check analyses from each model
        stage3: List of model rankings (informed by fact-checks)
        stage4: Final synthesized response with fact-check validation
    """
    if USE_SQLITE_DB:
        add_assistant_message_db(conversation_id, stage1, fact_check, stage3, stage4)
        return
    
    # JSON backend (legacy)
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "fact_check": fact_check,
        "stage3": stage3,
        "stage4": stage4,
        "timestamp": datetime.utcnow().isoformat()
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    if USE_SQLITE_DB:
        update_conversation_title_db(conversation_id, title)
        return
    
    # JSON backend (legacy)
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)
