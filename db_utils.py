#!/usr/bin/env python3
"""
Database management utility for LLM Council.

Usage:
    python db_utils.py stats        # Show database statistics
    python db_utils.py vacuum       # Optimize database
    python db_utils.py backup       # Create a backup
    python db_utils.py query        # Run a custom SQL query
"""

import sys
import os
import shutil
from datetime import datetime

# Ensure we're using SQLite
os.environ['USE_SQLITE_DB'] = 'true'

from backend.database import DB_FILE, get_db, init_database


def show_stats():
    """Show database statistics."""
    print("\n" + "=" * 70)
    print("DATABASE STATISTICS")
    print("=" * 70)
    
    if not os.path.exists(DB_FILE):
        print("\n❌ Database file not found. Run the app first to create it.")
        return
    
    init_database()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # File size
        file_size = os.path.getsize(DB_FILE)
        print(f"\n📁 File: {DB_FILE}")
        print(f"   Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        
        # Conversations
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        print(f"\n💬 Conversations: {conv_count:,}")
        
        if conv_count > 0:
            cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM conversations")
            oldest, newest = cursor.fetchone()
            print(f"   Oldest: {oldest}")
            print(f"   Newest: {newest}")
        
        # Messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        msg_count = cursor.fetchone()[0]
        print(f"\n📨 Messages: {msg_count:,}")
        
        cursor.execute("SELECT role, COUNT(*) FROM messages GROUP BY role")
        for row in cursor.fetchall():
            print(f"   {row[0].capitalize()}: {row[1]:,}")
        
        # Errors
        cursor.execute("SELECT COUNT(*) FROM errors")
        error_count = cursor.fetchone()[0]
        print(f"\n⚠️  Errors: {error_count:,}")
        
        if error_count > 0:
            cursor.execute("""
                SELECT model, COUNT(*) as count 
                FROM errors 
                GROUP BY model 
                ORDER BY count DESC 
                LIMIT 5
            """)
            print("   Top models by errors:")
            for row in cursor.fetchall():
                print(f"     • {row[0]}: {row[1]:,}")
            
            cursor.execute("""
                SELECT error_type, COUNT(*) as count 
                FROM errors 
                GROUP BY error_type 
                ORDER BY count DESC 
                LIMIT 5
            """)
            print("   Top error types:")
            for row in cursor.fetchall():
                print(f"     • {row[0]}: {row[1]:,}")
    
    print("\n" + "=" * 70 + "\n")


def vacuum_db():
    """Optimize the database by running VACUUM."""
    print("\n" + "=" * 70)
    print("DATABASE OPTIMIZATION")
    print("=" * 70)
    
    if not os.path.exists(DB_FILE):
        print("\n❌ Database file not found.")
        return
    
    original_size = os.path.getsize(DB_FILE)
    print(f"\nOriginal size: {original_size:,} bytes ({original_size / 1024:.2f} KB)")
    print("Running VACUUM... ", end="", flush=True)
    
    with get_db() as conn:
        conn.execute("VACUUM")
    
    new_size = os.path.getsize(DB_FILE)
    saved = original_size - new_size
    percent = (saved / original_size * 100) if original_size > 0 else 0
    
    print("✓")
    print(f"New size: {new_size:,} bytes ({new_size / 1024:.2f} KB)")
    print(f"Saved: {saved:,} bytes ({percent:.1f}%)")
    print("\n" + "=" * 70 + "\n")


def backup_db():
    """Create a backup of the database."""
    print("\n" + "=" * 70)
    print("DATABASE BACKUP")
    print("=" * 70)
    
    if not os.path.exists(DB_FILE):
        print("\n❌ Database file not found.")
        return
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f"llm_council_{timestamp}.db")
    
    print(f"\nBacking up to: {backup_file}")
    shutil.copy2(DB_FILE, backup_file)
    
    backup_size = os.path.getsize(backup_file)
    print(f"✓ Backup created ({backup_size:,} bytes)")
    print("\n" + "=" * 70 + "\n")


def run_query():
    """Run a custom SQL query."""
    print("\n" + "=" * 70)
    print("CUSTOM SQL QUERY")
    print("=" * 70)
    
    if not os.path.exists(DB_FILE):
        print("\n❌ Database file not found.")
        return
    
    print("\nEnter your SQL query (press Enter twice to execute):")
    print("Example: SELECT COUNT(*) FROM conversations;")
    print()
    
    lines = []
    while True:
        line = input()
        if not line and lines:
            break
        if line:
            lines.append(line)
    
    query = " ".join(lines)
    
    if not query.strip():
        print("\n❌ No query entered.")
        return
    
    print(f"\nExecuting: {query}")
    print("-" * 70)
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # If it's a SELECT query, fetch and display results
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                
                if not rows:
                    print("No results.")
                else:
                    # Print column names
                    col_names = [desc[0] for desc in cursor.description]
                    print(" | ".join(col_names))
                    print("-" * 70)
                    
                    # Print rows
                    for row in rows:
                        print(" | ".join(str(val) for val in row))
                    
                    print(f"\n{len(rows)} row(s) returned.")
            else:
                print(f"✓ Query executed successfully. {cursor.rowcount} row(s) affected.")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70 + "\n")


def show_help():
    """Show help message."""
    print("""
Database Management Utility for LLM Council

Usage:
    python db_utils.py <command>

Commands:
    stats     Show database statistics (tables, counts, file size)
    vacuum    Optimize database and reclaim space
    backup    Create a timestamped backup
    query     Run a custom SQL query interactively
    help      Show this help message

Examples:
    python db_utils.py stats
    python db_utils.py vacuum
    python db_utils.py backup
    python db_utils.py query

For more information, see DATABASE_MIGRATION.md
    """)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'stats': show_stats,
        'vacuum': vacuum_db,
        'backup': backup_db,
        'query': run_query,
        'help': show_help,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"\n❌ Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
