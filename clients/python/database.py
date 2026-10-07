"""Durable identity, conversation, and outgoing queue."""
import sqlite3
from pathlib import Path

from models import Message


class Database:
    def __init__(self, path):
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(Path(path).expanduser()))
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS identity (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL UNIQUE,
                    sender TEXT NOT NULL, recipient TEXT NOT NULL,
                    text TEXT NOT NULL, created_at TEXT NOT NULL,
                    delivery_state TEXT NOT NULL CHECK(delivery_state IN
                        ('PENDING', 'SENDING', 'SENT', 'RECEIVED'))
                );
            """)
            self.connection.execute(
                "UPDATE messages SET delivery_state='PENDING' WHERE delivery_state='SENDING'")

    @property
    def user(self):
        row = self.connection.execute("SELECT name FROM identity").fetchone()
        return row[0] if row else None

    def set_user(self, name):
        with self.connection:
            self.connection.execute("INSERT INTO identity VALUES (1, ?)", (name,))

    def insert(self, message, state):
        with self.connection:
            cursor = self.connection.execute("""
                INSERT INTO messages (message_id, sender, recipient, text, created_at, delivery_state)
                VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(message_id) DO NOTHING
            """, (*message.payload().values(), state))
        return cursor.rowcount == 1

    def state(self, message_id, state):
        with self.connection:
            self.connection.execute("UPDATE messages SET delivery_state=? WHERE message_id=?",
                                    (state, message_id))

    def pending(self):
        rows = self.connection.execute("""SELECT * FROM messages
            WHERE delivery_state='PENDING' ORDER BY sequence""").fetchall()
        return [Message(**{key: row[key] for key in Message.__dataclass_fields__}) for row in rows]

    def conversation(self, other):
        return self.connection.execute("""SELECT * FROM messages WHERE
            (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY sequence
        """, (self.user, other, other, self.user)).fetchall()

    def get(self, message_id):
        return self.connection.execute("SELECT * FROM messages WHERE message_id=?",
                                       (message_id,)).fetchone()

    def close(self):
        self.connection.close()
