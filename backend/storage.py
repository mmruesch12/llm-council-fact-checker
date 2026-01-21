"""Storage module for conversations - delegates to SQLite database with user associations."""

from typing import List, Dict, Any, Optional

from . import database as db


def create_conversation(conversation_id: str, user_id: str = "anonymous") -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation
        user_id: User's identifier (e.g., GitHub username)

    Returns:
        New conversation dict
    """
    return db.create_conversation(conversation_id, user_id)


def get_conversation(conversation_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation
        user_id: Optional user ID to verify ownership

    Returns:
        Conversation dict or None if not found
    """
    return db.get_conversation(conversation_id, user_id)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    db.save_conversation(conversation)


def list_conversations(user_id: str = None) -> List[Dict[str, Any]]:
    """
    List all conversations for a user (metadata only).

    Args:
        user_id: User's identifier. If None, returns empty list.

    Returns:
        List of conversation metadata dicts
    """
    if user_id is None:
        return []
    return db.list_conversations(user_id)


def search_conversations(user_id: str = None, search_query: str = "") -> List[Dict[str, Any]]:
    """
    Search conversations for a user by title or message content.

    Args:
        user_id: User's identifier. If None, returns empty list.
        search_query: Search query string

    Returns:
        List of matching conversation metadata dicts
    """
    if user_id is None:
        return []
    return db.search_conversations(user_id, search_query)


def add_user_message(conversation_id: str, content: str, user_id: str = None):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
        user_id: Optional user ID to verify ownership
    """
    db.add_user_message(conversation_id, content, user_id)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    fact_check: List[Dict[str, Any]],
    stage3: List[Dict[str, Any]],
    stage4: Dict[str, Any],
    user_id: str = None
):
    """
    Add an assistant message with all 4 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        fact_check: List of fact-check analyses from each model
        stage3: List of model rankings (informed by fact-checks)
        stage4: Final synthesized response with fact-check validation
        user_id: Optional user ID to verify ownership
    """
    db.add_assistant_message(conversation_id, stage1, fact_check, stage3, stage4, user_id)


def update_conversation_title(conversation_id: str, title: str, user_id: str = None):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
        user_id: Optional user ID to verify ownership
    """
    db.update_conversation_title(conversation_id, title, user_id)


def delete_conversation(conversation_id: str, user_id: str = None) -> bool:
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: Conversation identifier
        user_id: Optional user ID to verify ownership

    Returns:
        True if deleted, False if not found
    """
    return db.delete_conversation(conversation_id, user_id)
