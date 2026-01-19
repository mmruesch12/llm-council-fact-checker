"""
Simple test script for SQLite database functionality.

Run this to verify the database implementation works correctly.
"""

import os
import sys
import uuid

# Set environment variable to use SQLite
os.environ['USE_SQLITE_DB'] = 'true'

from backend.database import (
    init_database,
    create_conversation_db,
    get_conversation_db,
    list_conversations_db,
    add_user_message_db,
    add_assistant_message_db,
    update_conversation_title_db,
    add_errors_db,
    get_all_errors_db,
    get_error_summary_db,
    clear_error_catalog_db,
)


def test_conversations():
    """Test conversation CRUD operations."""
    print("\n=== Testing Conversation Operations ===")
    
    # Create a test conversation
    conv_id = str(uuid.uuid4())
    print(f"Creating conversation: {conv_id}")
    conversation = create_conversation_db(conv_id)
    assert conversation['id'] == conv_id
    assert conversation['title'] == 'New Conversation'
    print("✓ Conversation created")
    
    # Update title
    new_title = "Test Conversation"
    update_conversation_title_db(conv_id, new_title)
    conversation = get_conversation_db(conv_id)
    assert conversation['title'] == new_title
    print("✓ Title updated")
    
    # Add user message
    add_user_message_db(conv_id, "What is the capital of France?")
    conversation = get_conversation_db(conv_id)
    assert len(conversation['messages']) == 1
    assert conversation['messages'][0]['role'] == 'user'
    assert conversation['messages'][0]['content'] == "What is the capital of France?"
    print("✓ User message added")
    
    # Add assistant message
    stage1 = [
        {"model": "gpt-4", "response": "Paris", "time_ms": 100},
        {"model": "claude", "response": "Paris", "time_ms": 120}
    ]
    fact_check = [
        {"model": "gpt-4", "fact_check": "Accurate", "parsed_summary": {}}
    ]
    stage3 = [
        {"model": "gpt-4", "ranking": "1. Response A", "parsed_ranking": []}
    ]
    stage4 = {"chairman_response": "The capital of France is Paris."}
    
    add_assistant_message_db(conv_id, stage1, fact_check, stage3, stage4)
    conversation = get_conversation_db(conv_id)
    assert len(conversation['messages']) == 2
    assert conversation['messages'][1]['role'] == 'assistant'
    assert len(conversation['messages'][1]['stage1']) == 2
    print("✓ Assistant message added")
    
    # List conversations
    conversations = list_conversations_db()
    assert len(conversations) >= 1
    found = False
    for c in conversations:
        if c['id'] == conv_id:
            assert c['title'] == new_title
            assert c['message_count'] == 2
            found = True
            break
    assert found
    print("✓ Conversation listed correctly")
    
    print("✓ All conversation tests passed!\n")


def test_error_catalog():
    """Test error catalog operations."""
    print("=== Testing Error Catalog Operations ===")
    
    # Clear existing errors
    clear_error_catalog_db()
    
    # Add errors
    errors = [
        {
            "model": "gpt-4",
            "error_type": "Hallucinated Fact",
            "claim": "The moon is made of cheese",
            "explanation": "This is a well-known myth",
            "question_summary": "What is the moon made of?",
            "conversation_id": "test-conv-1"
        },
        {
            "model": "claude",
            "error_type": "Numerical/Statistical Error",
            "claim": "Earth has 2 moons",
            "explanation": "Earth has only 1 moon",
            "question_summary": "How many moons does Earth have?",
            "conversation_id": "test-conv-2"
        },
        {
            "model": "gpt-4",
            "error_type": "Numerical/Statistical Error",
            "claim": "Pi equals 3",
            "explanation": "Pi is approximately 3.14159",
            "question_summary": "What is Pi?",
            "conversation_id": "test-conv-3"
        }
    ]
    
    add_errors_db(errors)
    print("✓ Errors added")
    
    # Get all errors
    all_errors = get_all_errors_db()
    assert len(all_errors) == 3
    print(f"✓ Retrieved {len(all_errors)} errors")
    
    # Get error summary
    summary = get_error_summary_db()
    assert summary['total_errors'] == 3
    assert summary['by_model']['gpt-4'] == 2
    assert summary['by_model']['claude'] == 1
    assert summary['by_type']['Hallucinated Fact'] == 1
    assert summary['by_type']['Numerical/Statistical Error'] == 2
    print("✓ Error summary correct")
    
    # Clear errors
    clear_error_catalog_db()
    all_errors = get_all_errors_db()
    assert len(all_errors) == 0
    print("✓ Errors cleared")
    
    print("✓ All error catalog tests passed!\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING SQLITE DATABASE IMPLEMENTATION")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    init_database()
    print("✓ Database initialized")
    
    try:
        test_conversations()
        test_error_catalog()
        
        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print("\nThe SQLite database is working correctly.")
        print("You can now use it by ensuring USE_SQLITE_DB=true in your .env file\n")
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
