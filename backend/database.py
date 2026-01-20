"""SQLite database module for conversation storage with user associations."""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from .config import DATABASE_PATH


def get_db_path() -> str:
    """Get the database file path, creating parent directories if needed."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return DATABASE_PATH


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database schema if it doesn't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                stage1 TEXT,
                fact_check TEXT,
                stage3 TEXT,
                stage4 TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
            ON conversations(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
            ON messages(conversation_id)
        """)
        
        conn.commit()


def create_conversation(conversation_id: str, user_id: str) -> Dict[str, Any]:
    """
    Create a new conversation for a user.
    
    Args:
        conversation_id: Unique identifier for the conversation
        user_id: User's identifier (e.g., GitHub username)
    
    Returns:
        New conversation dict
    """
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (conversation_id, user_id, "New Conversation", now, now))
    
    return {
        "id": conversation_id,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "title": "New Conversation",
        "messages": []
    }


def get_conversation(conversation_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from the database.
    
    Args:
        conversation_id: Unique identifier for the conversation
        user_id: Optional user ID to verify ownership
    
    Returns:
        Conversation dict or None if not found (or not owned by user)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations
                WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))
        else:
            cursor.execute("""
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
            """, (conversation_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        conversation = {
            "id": row["id"],
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "title": row["title"],
            "messages": []
        }
        
        # Load messages
        cursor.execute("""
            SELECT role, content, stage1, fact_check, stage3, stage4, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,))
        
        for msg_row in cursor.fetchall():
            if msg_row["role"] == "user":
                conversation["messages"].append({
                    "role": "user",
                    "content": msg_row["content"],
                    "timestamp": msg_row["timestamp"]
                })
            else:
                conversation["messages"].append({
                    "role": "assistant",
                    "stage1": json.loads(msg_row["stage1"]) if msg_row["stage1"] else None,
                    "fact_check": json.loads(msg_row["fact_check"]) if msg_row["fact_check"] else None,
                    "stage3": json.loads(msg_row["stage3"]) if msg_row["stage3"] else None,
                    "stage4": json.loads(msg_row["stage4"]) if msg_row["stage4"] else None,
                    "timestamp": msg_row["timestamp"]
                })
        
        return conversation


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to the database.
    Note: This updates the conversation metadata. Messages are saved separately.
    
    Args:
        conversation: Conversation dict to save
    """
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
        """, (conversation.get("title", "New Conversation"), now, conversation["id"]))


def list_conversations(user_id: str) -> List[Dict[str, Any]]:
    """
    List all conversations for a specific user (metadata only).
    
    Args:
        user_id: User's identifier
    
    Returns:
        List of conversation metadata dicts
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """, (user_id,))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "title": row["title"],
                "message_count": row["message_count"]
            })
        
        return conversations


def add_user_message(conversation_id: str, content: str, user_id: str = None):
    """
    Add a user message to a conversation.
    
    Args:
        conversation_id: Conversation identifier
        content: User message content
        user_id: Optional user ID to verify ownership
    """
    # Verify conversation exists (and optionally belongs to user)
    conversation = get_conversation(conversation_id, user_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, 'user', ?, ?)
        """, (conversation_id, content, now))
        
        # Update conversation's updated_at timestamp
        cursor.execute("""
            UPDATE conversations SET updated_at = ? WHERE id = ?
        """, (now, conversation_id))


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
    # Verify conversation exists (and optionally belongs to user)
    conversation = get_conversation(conversation_id, user_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, stage1, fact_check, stage3, stage4, timestamp)
            VALUES (?, 'assistant', ?, ?, ?, ?, ?)
        """, (
            conversation_id,
            json.dumps(stage1),
            json.dumps(fact_check),
            json.dumps(stage3),
            json.dumps(stage4),
            now
        ))
        
        # Update conversation's updated_at timestamp
        cursor.execute("""
            UPDATE conversations SET updated_at = ? WHERE id = ?
        """, (now, conversation_id))


def update_conversation_title(conversation_id: str, title: str, user_id: str = None):
    """
    Update the title of a conversation.
    
    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
        user_id: Optional user ID to verify ownership
    """
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (title, now, conversation_id, user_id))
        else:
            cursor.execute("""
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
            """, (title, now, conversation_id))
        
        if cursor.rowcount == 0:
            raise ValueError(f"Conversation {conversation_id} not found")


def delete_conversation(conversation_id: str, user_id: str = None) -> bool:
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: Conversation identifier
        user_id: Optional user ID to verify ownership
    
    Returns:
        True if deleted, False if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Delete messages first (due to foreign key)
        cursor.execute("""
            DELETE FROM messages WHERE conversation_id = ?
        """, (conversation_id,))
        
        # Delete conversation
        if user_id:
            cursor.execute("""
                DELETE FROM conversations WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))
        else:
            cursor.execute("""
                DELETE FROM conversations WHERE id = ?
            """, (conversation_id,))
        
        return cursor.rowcount > 0


# Initialize database on module import
init_database()
