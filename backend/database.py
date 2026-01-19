"""SQLite database module for conversation and error storage."""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import contextmanager

from .config import DATA_DIR


# Database file path
DB_FILE = os.path.join(os.path.dirname(DATA_DIR), "llm_council.db")


@contextmanager
def get_db():
    """
    Context manager for database connections.
    Ensures proper connection handling and automatic commit/rollback.
    """
    # Ensure the directory exists
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """
    Initialize the database with required tables and indexes.
    Safe to call multiple times - only creates tables if they don't exist.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                user_id TEXT
            )
        """)
        
        # Messages table
        # Store JSON data as TEXT for stage1, fact_check, stage3, stage4
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                stage1_json TEXT,
                fact_check_json TEXT,
                stage3_json TEXT,
                stage4_json TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # Errors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                model TEXT NOT NULL,
                error_type TEXT NOT NULL,
                claim TEXT,
                explanation TEXT,
                question_summary TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_created 
            ON conversations(created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_errors_model 
            ON errors(model)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_errors_type 
            ON errors(error_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_errors_conversation 
            ON errors(conversation_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_errors_timestamp 
            ON errors(timestamp DESC)
        """)


# ============================================================================
# Conversation Operations
# ============================================================================

def create_conversation_db(conversation_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new conversation in the database.
    
    Args:
        conversation_id: Unique identifier for the conversation
        user_id: Optional user identifier
        
    Returns:
        New conversation dict
    """
    init_database()
    
    created_at = datetime.utcnow().isoformat()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO conversations (id, created_at, title, user_id) 
               VALUES (?, ?, ?, ?)""",
            (conversation_id, created_at, "New Conversation", user_id)
        )
    
    return {
        "id": conversation_id,
        "created_at": created_at,
        "title": "New Conversation",
        "messages": []
    }


def get_conversation_db(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from the database.
    
    Args:
        conversation_id: Unique identifier for the conversation
        
    Returns:
        Conversation dict with messages or None if not found
    """
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get conversation metadata
        cursor.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        conversation = {
            "id": row["id"],
            "created_at": row["created_at"],
            "title": row["title"],
            "messages": []
        }
        
        # Get all messages for this conversation
        cursor.execute(
            """SELECT * FROM messages 
               WHERE conversation_id = ? 
               ORDER BY timestamp ASC""",
            (conversation_id,)
        )
        
        for msg_row in cursor.fetchall():
            message = {
                "role": msg_row["role"],
                "timestamp": msg_row["timestamp"]
            }
            
            if msg_row["role"] == "user":
                message["content"] = msg_row["content"]
            else:  # assistant
                # Parse JSON fields
                if msg_row["stage1_json"]:
                    message["stage1"] = json.loads(msg_row["stage1_json"])
                if msg_row["fact_check_json"]:
                    message["fact_check"] = json.loads(msg_row["fact_check_json"])
                if msg_row["stage3_json"]:
                    message["stage3"] = json.loads(msg_row["stage3_json"])
                if msg_row["stage4_json"]:
                    message["stage4"] = json.loads(msg_row["stage4_json"])
            
            conversation["messages"].append(message)
        
        return conversation


def list_conversations_db() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).
    
    Returns:
        List of conversation metadata dicts
    """
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.created_at, c.title, COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id, c.created_at, c.title
            ORDER BY c.created_at DESC
        """)
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "id": row["id"],
                "created_at": row["created_at"],
                "title": row["title"],
                "message_count": row["message_count"]
            })
        
        return conversations


def add_user_message_db(conversation_id: str, content: str):
    """
    Add a user message to a conversation.
    
    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if conversation exists
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if cursor.fetchone() is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        timestamp = datetime.utcnow().isoformat()
        cursor.execute(
            """INSERT INTO messages (conversation_id, role, content, timestamp)
               VALUES (?, ?, ?, ?)""",
            (conversation_id, "user", content, timestamp)
        )


def add_assistant_message_db(
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
        fact_check: List of fact-check analyses
        stage3: List of model rankings
        stage4: Final synthesized response
    """
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if conversation exists
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if cursor.fetchone() is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        timestamp = datetime.utcnow().isoformat()
        
        # Convert stage data to JSON strings
        stage1_json = json.dumps(stage1)
        fact_check_json = json.dumps(fact_check)
        stage3_json = json.dumps(stage3)
        stage4_json = json.dumps(stage4)
        
        cursor.execute(
            """INSERT INTO messages 
               (conversation_id, role, stage1_json, fact_check_json, stage3_json, stage4_json, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, "assistant", stage1_json, fact_check_json, stage3_json, stage4_json, timestamp)
        )


def update_conversation_title_db(conversation_id: str, title: str):
    """
    Update the title of a conversation.
    
    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        
        if cursor.rowcount == 0:
            raise ValueError(f"Conversation {conversation_id} not found")


# ============================================================================
# Error Catalog Operations
# ============================================================================

def add_errors_db(errors: List[Dict[str, Any]]):
    """
    Add classified errors to the database.
    
    Args:
        errors: List of error dicts with keys:
            - model: The model that made the error
            - error_type: Type of error
            - claim: The inaccurate claim
            - explanation: Why it's wrong
            - question_summary: Summary of the question
            - conversation_id: ID of the conversation
    """
    if not errors:
        return
    
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for error in errors:
            import uuid
            error_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            cursor.execute(
                """INSERT INTO errors 
                   (id, conversation_id, model, error_type, claim, explanation, question_summary, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    error_id,
                    error.get("conversation_id"),
                    error.get("model", "unknown"),
                    error.get("error_type", "Other"),
                    error.get("claim", ""),
                    error.get("explanation", ""),
                    error.get("question_summary", ""),
                    timestamp
                )
            )


def get_all_errors_db() -> List[Dict[str, Any]]:
    """Get all errors from the database."""
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM errors ORDER BY timestamp DESC")
        
        errors = []
        for row in cursor.fetchall():
            errors.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "conversation_id": row["conversation_id"],
                "model": row["model"],
                "error_type": row["error_type"],
                "claim": row["claim"],
                "explanation": row["explanation"],
                "question_summary": row["question_summary"]
            })
        
        return errors


def get_errors_by_model_db(model: str) -> List[Dict[str, Any]]:
    """Get all errors for a specific model."""
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM errors WHERE model = ? ORDER BY timestamp DESC",
            (model,)
        )
        
        errors = []
        for row in cursor.fetchall():
            errors.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "conversation_id": row["conversation_id"],
                "model": row["model"],
                "error_type": row["error_type"],
                "claim": row["claim"],
                "explanation": row["explanation"],
                "question_summary": row["question_summary"]
            })
        
        return errors


def get_errors_by_type_db(error_type: str) -> List[Dict[str, Any]]:
    """Get all errors of a specific type."""
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM errors WHERE error_type = ? ORDER BY timestamp DESC",
            (error_type,)
        )
        
        errors = []
        for row in cursor.fetchall():
            errors.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "conversation_id": row["conversation_id"],
                "model": row["model"],
                "error_type": row["error_type"],
                "claim": row["claim"],
                "explanation": row["explanation"],
                "question_summary": row["question_summary"]
            })
        
        return errors


def get_error_summary_db() -> Dict[str, Any]:
    """
    Get a summary of errors by model and by type.
    
    Returns:
        Dict with 'by_model', 'by_type', and 'by_model_and_type' breakdowns
    """
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total errors
        cursor.execute("SELECT COUNT(*) as total FROM errors")
        total_errors = cursor.fetchone()["total"]
        
        # By model
        cursor.execute("""
            SELECT model, COUNT(*) as count 
            FROM errors 
            GROUP BY model
            ORDER BY count DESC
        """)
        by_model = {row["model"]: row["count"] for row in cursor.fetchall()}
        
        # By type
        cursor.execute("""
            SELECT error_type, COUNT(*) as count 
            FROM errors 
            GROUP BY error_type
            ORDER BY count DESC
        """)
        by_type = {row["error_type"]: row["count"] for row in cursor.fetchall()}
        
        # By model and type
        cursor.execute("""
            SELECT model, error_type, COUNT(*) as count 
            FROM errors 
            GROUP BY model, error_type
            ORDER BY model, count DESC
        """)
        by_model_and_type = {}
        for row in cursor.fetchall():
            model = row["model"]
            error_type = row["error_type"]
            count = row["count"]
            
            if model not in by_model_and_type:
                by_model_and_type[model] = {}
            by_model_and_type[model][error_type] = count
        
        return {
            "total_errors": total_errors,
            "by_model": by_model,
            "by_type": by_type,
            "by_model_and_type": by_model_and_type
        }


def clear_error_catalog_db():
    """Clear all errors from the database."""
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM errors")
