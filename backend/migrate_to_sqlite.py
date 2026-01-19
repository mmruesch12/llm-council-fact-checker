"""
Migration utility to move data from JSON files to SQLite database.

Usage:
    python -m backend.migrate_to_sqlite

This script will:
1. Read all conversation JSON files from data/conversations/
2. Read error catalog from data/error_catalog.json
3. Import all data into the SQLite database
4. Verify the migration was successful
5. Optionally backup and remove old JSON files
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from .config import DATA_DIR, ERROR_CATALOG_FILE
from .database import (
    init_database,
    create_conversation_db,
    add_user_message_db,
    add_assistant_message_db,
    update_conversation_title_db,
    add_errors_db,
    get_conversation_db,
    get_all_errors_db,
)


def migrate_conversations():
    """Migrate all conversations from JSON to SQLite."""
    print("=" * 60)
    print("MIGRATING CONVERSATIONS")
    print("=" * 60)
    
    if not os.path.exists(DATA_DIR):
        print(f"No conversations directory found at {DATA_DIR}")
        return 0
    
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    
    if not json_files:
        print("No conversation files found to migrate")
        return 0
    
    print(f"Found {len(json_files)} conversation files to migrate")
    
    migrated_count = 0
    error_count = 0
    
    for filename in json_files:
        filepath = os.path.join(DATA_DIR, filename)
        
        try:
            with open(filepath, 'r') as f:
                conversation = json.load(f)
            
            conversation_id = conversation['id']
            title = conversation.get('title', 'New Conversation')
            
            print(f"\nMigrating conversation: {conversation_id}")
            print(f"  Title: {title}")
            print(f"  Messages: {len(conversation.get('messages', []))}")
            
            # Check if already exists in database
            existing = get_conversation_db(conversation_id)
            if existing:
                print(f"  ⚠ Conversation {conversation_id} already exists in database, skipping")
                continue
            
            # Create conversation
            create_conversation_db(conversation_id)
            
            # Update title if not default
            if title != 'New Conversation':
                update_conversation_title_db(conversation_id, title)
            
            # Add messages
            for msg in conversation.get('messages', []):
                if msg['role'] == 'user':
                    add_user_message_db(conversation_id, msg['content'])
                elif msg['role'] == 'assistant':
                    add_assistant_message_db(
                        conversation_id,
                        msg.get('stage1', []),
                        msg.get('fact_check', []),
                        msg.get('stage3', []),
                        msg.get('stage4', {})
                    )
            
            print(f"  ✓ Successfully migrated")
            migrated_count += 1
            
        except Exception as e:
            print(f"  ✗ Error migrating {filename}: {e}")
            error_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"Conversations migration complete:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Errors: {error_count}")
    print(f"  Skipped: {len(json_files) - migrated_count - error_count}")
    print(f"{'=' * 60}\n")
    
    return migrated_count


def migrate_error_catalog():
    """Migrate error catalog from JSON to SQLite."""
    print("=" * 60)
    print("MIGRATING ERROR CATALOG")
    print("=" * 60)
    
    if not os.path.exists(ERROR_CATALOG_FILE):
        print(f"No error catalog found at {ERROR_CATALOG_FILE}")
        return 0
    
    try:
        with open(ERROR_CATALOG_FILE, 'r') as f:
            catalog = json.load(f)
        
        errors = catalog.get('errors', [])
        
        if not errors:
            print("No errors found in catalog")
            return 0
        
        print(f"Found {len(errors)} errors to migrate")
        
        # Add all errors to database
        add_errors_db(errors)
        
        # Verify migration
        db_errors = get_all_errors_db()
        print(f"✓ Successfully migrated {len(db_errors)} errors")
        
        print(f"{'=' * 60}\n")
        return len(errors)
        
    except Exception as e:
        print(f"✗ Error migrating error catalog: {e}")
        print(f"{'=' * 60}\n")
        return 0


def verify_migration():
    """Verify the migration was successful."""
    print("=" * 60)
    print("VERIFYING MIGRATION")
    print("=" * 60)
    
    # Import here to use SQLite backend
    from .database import list_conversations_db, get_error_summary_db
    
    conversations = list_conversations_db()
    error_summary = get_error_summary_db()
    
    print(f"Database contains:")
    print(f"  Conversations: {len(conversations)}")
    print(f"  Total Errors: {error_summary['total_errors']}")
    
    if conversations:
        total_messages = sum(c['message_count'] for c in conversations)
        print(f"  Total Messages: {total_messages}")
    
    print(f"{'=' * 60}\n")


def backup_json_files():
    """Create a backup of JSON files before deletion."""
    backup_dir = "data/json_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 60)
    print("BACKING UP JSON FILES")
    print("=" * 60)
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup conversations
    if os.path.exists(DATA_DIR):
        conv_backup = os.path.join(backup_dir, "conversations")
        shutil.copytree(DATA_DIR, conv_backup)
        print(f"✓ Backed up conversations to: {conv_backup}")
    
    # Backup error catalog
    if os.path.exists(ERROR_CATALOG_FILE):
        error_backup = os.path.join(backup_dir, "error_catalog.json")
        shutil.copy2(ERROR_CATALOG_FILE, error_backup)
        print(f"✓ Backed up error catalog to: {error_backup}")
    
    print(f"{'=' * 60}\n")
    return backup_dir


def main():
    """Run the migration."""
    print("\n")
    print("=" * 60)
    print("LLM COUNCIL - JSON TO SQLITE MIGRATION")
    print("=" * 60)
    print("\nThis script will migrate your data from JSON files to SQLite.")
    print("Your original JSON files will be backed up before any changes.\n")
    
    # Initialize database
    print("Initializing SQLite database...")
    init_database()
    print("✓ Database initialized\n")
    
    # Migrate data
    conv_count = migrate_conversations()
    error_count = migrate_error_catalog()
    
    # Verify
    verify_migration()
    
    # Backup and cleanup
    if conv_count > 0 or error_count > 0:
        print("Migration successful!")
        response = input("\nDo you want to backup and remove the old JSON files? (y/N): ")
        
        if response.lower() == 'y':
            backup_dir = backup_json_files()
            
            print("\nRemoving old JSON files...")
            if os.path.exists(DATA_DIR):
                shutil.rmtree(DATA_DIR)
                print(f"✓ Removed {DATA_DIR}")
            
            if os.path.exists(ERROR_CATALOG_FILE):
                os.remove(ERROR_CATALOG_FILE)
                print(f"✓ Removed {ERROR_CATALOG_FILE}")
            
            print(f"\n✓ Migration complete! Backup saved to: {backup_dir}")
        else:
            print("\nJSON files kept. You can manually remove them after verifying the migration.")
    else:
        print("No data was migrated.")
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print("\nTo use the SQLite database, ensure USE_SQLITE_DB=true in your .env file")
    print("(This is the default setting)\n")


if __name__ == "__main__":
    main()
