"""
Message Persistence Database
Stores and retrieves chat messages using SQLite

Features:
- Store group messages (receiver = NULL)
- Store private messages (receiver = username)
- Retrieve message history for users
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Tuple, Optional
import logging

DATABASE_FILE = "chat_messages.db"

class MessageDatabase:
    """
    Thread-safe database for storing and retrieving chat messages
    """
    
    def __init__(self, db_file: str = DATABASE_FILE):
        self.db_file = db_file
        self.lock = threading.Lock()
        self._init_database()
        logging.info(f"[DB] Database initialized: {db_file}")
    
    def _init_database(self):
        """Initialize database tables if they don't exist"""
        with self.lock:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    receiver TEXT,  -- NULL for group messages, username for private
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_type TEXT DEFAULT 'group'  -- 'group' or 'private'
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_messages 
                ON messages(sender, receiver, timestamp)
            """)
            
            conn.commit()
            conn.close()
    
    def save_message(self, sender: str, message: str, receiver: Optional[str] = None):
        """
        Save a message to the database
        Args:
            sender: Username of the sender
            message: Message content
            receiver: Username of receiver (None for group messages)
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                message_type = 'private' if receiver else 'group'
                
                cursor.execute("""
                    INSERT INTO messages (sender, receiver, message, message_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (sender, receiver, message, message_type, datetime.now()))
                
                conn.commit()
                conn.close()
                
                logging.debug(f"[DB] Saved {message_type} message: {sender} -> {receiver or 'GROUP'}")
                
            except Exception as e:
                logging.error(f"[DB] Error saving message: {e}")
    
    def get_user_messages(self, username: str, limit: int = 100) -> List[Tuple]:
        """
        Retrieve all messages relevant to a user
        Returns: List of tuples (sender, receiver, message, timestamp, message_type)
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                # Get messages where user is sender or receiver, or group messages
                # Group messages are shown to everyone
                cursor.execute("""
                    SELECT sender, receiver, message, timestamp, message_type
                    FROM messages
                    WHERE sender = ? 
                       OR receiver = ?
                       OR (receiver IS NULL AND message_type = 'group')
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (username, username, limit))
                
                messages = cursor.fetchall()
                conn.close()
                
                logging.info(f"[DB] Retrieved {len(messages)} messages for {username}")
                if messages:
                    logging.debug(f"[DB] Sample message: {messages[0]}")
                return messages
                
            except Exception as e:
                logging.error(f"[DB] Error retrieving messages for {username}: {e}")
                import traceback
                logging.error(traceback.format_exc())
                return []
    
    def get_recent_group_messages(self, limit: int = 50) -> List[Tuple]:
        """
        Get recent group messages
        Returns: List of tuples (sender, receiver, message, timestamp, message_type)
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT sender, receiver, message, timestamp, message_type
                    FROM messages
                    WHERE message_type = 'group'
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                messages = cursor.fetchall()
                conn.close()
                
                return list(reversed(messages))  # Return in chronological order
                
            except Exception as e:
                logging.error(f"[DB] Error retrieving group messages: {e}")
                return []
    
    def get_private_messages(self, username1: str, username2: str, limit: int = 100) -> List[Tuple]:
        """
        Get private messages between two users
        Returns: List of tuples (sender, receiver, message, timestamp, message_type)
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT sender, receiver, message, timestamp, message_type
                    FROM messages
                    WHERE message_type = 'private'
                      AND ((sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?))
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (username1, username2, username2, username1, limit))
                
                messages = cursor.fetchall()
                conn.close()
                
                return messages
                
            except Exception as e:
                logging.error(f"[DB] Error retrieving private messages: {e}")
                return []
    
    def clear_messages(self):
        """Clear all messages from database (for testing/cleanup)"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                conn.commit()
                conn.close()
                logging.info("[DB] All messages cleared")
            except Exception as e:
                logging.error(f"[DB] Error clearing messages: {e}")

