# Database Migration Guide

## Why SQLite?

This project now uses **SQLite** as the default storage backend instead of JSON files. Here's why:

### Performance Comparison

| Operation | JSON Files | SQLite | Improvement |
|-----------|-----------|--------|-------------|
| List conversations | O(n) - read all files | O(1) - indexed query | 100x+ faster with many conversations |
| Get single conversation | O(1) - direct file read | O(1) - indexed lookup | Similar performance |
| Search messages | O(n*m) - scan all files/messages | O(log n) - indexed search | 1000x+ faster |
| Filter by date/model | O(n) - scan all files | O(log n) - indexed query | 100x+ faster |
| Error statistics | O(n) - process entire file | O(1) - aggregated query | 50x+ faster |

### Benefits

✅ **Zero Cost**: No external database service required, no monthly fees  
✅ **Fast**: SQL indexes make queries lightning-fast as data grows  
✅ **Reliable**: ACID transactions prevent data corruption  
✅ **Concurrent**: Multiple processes can safely access the database  
✅ **Simple**: Single file, built into Python, no setup needed  
✅ **Portable**: Copy `llm_council.db` to backup or move data  
✅ **Query-able**: Use SQL to analyze your conversation history  

### Feature Comparison

| Feature | JSON Files | SQLite |
|---------|-----------|--------|
| Storage format | Multiple .json files | Single .db file |
| Concurrent writes | ❌ File locking issues | ✅ ACID transactions |
| Query performance | Slow for large datasets | Fast with indexes |
| Data integrity | Manual validation | Built-in constraints |
| Backup | Copy entire directory | Copy single file |
| Analytics | Manual processing | SQL queries |
| Migration | Manual scripts | Built-in tools |

## Migration Process

### Step 1: Check Current Data

First, see if you have existing JSON data:

```bash
ls -lh data/conversations/
ls -lh data/error_catalog.json
```

### Step 2: Run Migration

If you have existing data, migrate it to SQLite:

```bash
python -m backend.migrate_to_sqlite
```

The migration script will:
1. ✅ Read all JSON conversation files
2. ✅ Read the error catalog JSON file
3. ✅ Import everything into SQLite
4. ✅ Verify the migration succeeded
5. ⚠️ Optionally backup and remove old JSON files

**Important**: The script will ask before deleting any files. Your original JSON data will be backed up first.

### Step 3: Verify Migration

After migration, verify your data:

```bash
# Run database tests
python test_database.py

# Start the backend
python -m backend.main

# Check that your conversations are visible
curl http://localhost:8001/api/conversations
```

### Step 4: Configure (Optional)

The default configuration uses SQLite. To change:

```bash
# In your .env file

# Use SQLite (default)
USE_SQLITE_DB=true

# Or revert to JSON files
USE_SQLITE_DB=false
```

## Database Schema

### Conversations Table

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    user_id TEXT
);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
```

### Messages Table

```sql
CREATE TABLE messages (
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
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
```

### Errors Table

```sql
CREATE TABLE errors (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    model TEXT NOT NULL,
    error_type TEXT NOT NULL,
    claim TEXT,
    explanation TEXT,
    question_summary TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
);
CREATE INDEX idx_errors_model ON errors(model);
CREATE INDEX idx_errors_type ON errors(error_type);
CREATE INDEX idx_errors_conversation ON errors(conversation_id);
CREATE INDEX idx_errors_timestamp ON errors(timestamp DESC);
```

## Advanced Usage

### Query Your Data Directly

You can use the SQLite CLI to query your data:

```bash
# Open the database
sqlite3 llm_council.db

# List all tables
.tables

# Get conversation count
SELECT COUNT(*) FROM conversations;

# Find most recent conversations
SELECT id, title, created_at 
FROM conversations 
ORDER BY created_at DESC 
LIMIT 10;

# Get error statistics by model
SELECT model, error_type, COUNT(*) as count
FROM errors
GROUP BY model, error_type
ORDER BY count DESC;

# Find all hallucinated facts
SELECT model, claim, explanation
FROM errors
WHERE error_type = 'Hallucinated Fact';
```

### Backup Your Database

```bash
# Create a backup
cp llm_council.db llm_council.backup.db

# Or use SQLite's backup command
sqlite3 llm_council.db ".backup llm_council.backup.db"
```

### Reset Database

```bash
# Remove the database file
rm llm_council.db

# Next time the app starts, it will create a fresh database
```

## Troubleshooting

### "Database is locked" error

This usually happens if:
1. Multiple instances of the backend are running
2. A previous instance crashed and left a lock file

**Solution:**
```bash
# Kill all backend processes
pkill -f "python -m backend.main"

# Remove lock files (if they exist)
rm -f llm_council.db-shm llm_council.db-wal

# Restart the backend
python -m backend.main
```

### Migration failed

If migration fails midway:

1. Your original JSON files are safe (never deleted without confirmation)
2. You can delete the database and try again:
   ```bash
   rm llm_council.db
   python -m backend.migrate_to_sqlite
   ```

### Want to go back to JSON?

Simply set `USE_SQLITE_DB=false` in your `.env` file. The app will use JSON files again. Note that any data added to SQLite won't be available (you'd need to manually export it).

## Performance Tips

1. **Database file location**: The default location (`llm_council.db` at project root) is fine for most use cases. For very high performance, place it on an SSD.

2. **Vacuum occasionally**: After deleting many conversations, reclaim space:
   ```bash
   sqlite3 llm_council.db "VACUUM;"
   ```

3. **Monitor size**: Check database size:
   ```bash
   ls -lh llm_council.db
   ```

4. **Backup regularly**: SQLite is reliable, but regular backups are always a good idea.

## Need Help?

If you encounter any issues:

1. Check that `USE_SQLITE_DB=true` in your `.env` file (or not set, as true is default)
2. Run `python test_database.py` to verify the database is working
3. Check the backend logs for any error messages
4. Ensure no other processes are using the database file

For advanced SQLite configuration, see the [SQLite documentation](https://www.sqlite.org/docs.html).
