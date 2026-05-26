"""
SQLite persistence layer for tasks and conversation memory
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from schemas import ConversationMessage
from utils import get_logger

logger = get_logger("persistence")


class PersistenceLayer:
    """SQLite-based persistence for tasks and conversation memory"""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT,
                due_date TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP
            )
        """)
        
        # Conversation memory table (lightweight, for recent context)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for timestamp-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_timestamp 
            ON conversation_memory(timestamp DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def save_task(self, title: str, description: Optional[str] = None, 
                  priority: Optional[str] = None, due_date: Optional[str] = None,
                  tags: Optional[List[str]] = None) -> int:
        """Save a task and return its ID"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tasks (title, description, priority, due_date, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            description,
            priority,
            due_date,
            json.dumps(tags) if tags else None,
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return task_id
    
    def get_tasks(self, completed: Optional[bool] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get tasks, optionally filtered by completion status"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if completed is not None:
            query += " AND completed = ?"
            params.append(1 if completed else 0)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            task = dict(row)
            if task['tags']:
                task['tags'] = json.loads(task['tags'])
            tasks.append(task)
        
        conn.close()
        return tasks
    
    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks 
            SET completed = 1, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (task_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def save_conversation_message(self, message: ConversationMessage) -> int:
        """Save a conversation message to memory"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_memory (role, content, metadata, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            message.role,
            message.content,
            json.dumps(message.metadata) if message.metadata else None,
            message.timestamp.isoformat() if isinstance(message.timestamp, datetime) else message.timestamp,
        ))
        
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return msg_id
    
    def get_recent_messages(self, limit: int = 50) -> List[ConversationMessage]:
        """Get recent conversation messages"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, metadata, timestamp
            FROM conversation_memory
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            role, content, metadata_json, timestamp = row
            metadata = json.loads(metadata_json) if metadata_json else None
            
            # Parse timestamp
            if isinstance(timestamp, str):
                try:
                    ts = datetime.fromisoformat(timestamp)
                except:
                    ts = datetime.now()
            else:
                ts = datetime.now()
            
            messages.append(ConversationMessage(
                role=role,
                content=content,
                metadata=metadata,
                timestamp=ts,
            ))
        
        return messages
    
    def clear_old_messages(self, keep_last_n: int = 100):
        """Clear old messages, keeping only the most recent N"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM conversation_memory
            WHERE id NOT IN (
                SELECT id FROM conversation_memory
                ORDER BY timestamp DESC
                LIMIT ?
            )
        """, (keep_last_n,))
        
        conn.commit()
        conn.close()

