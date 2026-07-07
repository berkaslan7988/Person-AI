"""Person AI - SQLite storage for characters, chat sessions, and messages.

Features:
- Character CRUD
- Session CRUD with per-character multi-session support
- Auto-save active session (append-only for now)
- Session metadata (title derived from first user message)
- Message search
- Last active session tracking
- Persistent app settings via the app_state table
"""

import sqlite3
import json
from typing import Optional

from ..config import DB_PATH
from ..models.character import Character
from ..models.chat_session import ChatSession, Message


SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    traits TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    greeting TEXT DEFAULT '',
    examples TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER,
    character_name TEXT DEFAULT '',
    title TEXT DEFAULT '',
    messages TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);
"""


class Storage:
    """Singleton-style storage manager (one DB file)."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    @property
    def connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
        return self.conn

    def _init_db(self):
        conn = self.connection
        conn.executescript(SCHEMA)
        conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ── App State Persistence ──────────────────────────────────

    def set_state(self, key: str, value: str):
        conn = self.connection
        conn.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_state(self, key: str, default: str = "") -> str:
        conn = self.connection
        row = conn.execute(
            "SELECT value FROM app_state WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def last_active_session_id(self) -> Optional[int]:
        val = self.get_state("last_active_session", "")
        return int(val) if val else None

    def set_last_active_session(self, session_id: int):
        self.set_state("last_active_session", str(session_id))

    # ── JSON helpers (corruption-tolerant) ─────────────────────

    @staticmethod
    def _list_from_json(raw: str) -> list:
        """Parse a JSON list column, tolerating corrupt rows."""
        try:
            data = json.loads(raw or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _messages_from_json(raw: str) -> list[Message]:
        """Parse a messages JSON column, tolerating corrupt rows."""
        try:
            msgs_raw = json.loads(raw or "[]")
        except (json.JSONDecodeError, TypeError):
            return []
        return [Message.from_dict(m) for m in msgs_raw if isinstance(m, dict)]

    # ── Characters ──────────────────────────────────────────────

    def save_character(self, char: Character) -> int:
        """Upsert a character. Returns its id."""
        conn = self.connection
        examples_json = json.dumps(char.examples, ensure_ascii=False)
        tags_json = json.dumps(char.tags, ensure_ascii=False)
        if char.id:
            conn.execute(
                """UPDATE characters SET name=?, traits=?, avatar_url=?, greeting=?, examples=?, tags=?
                   WHERE id=?""",
                (char.name, char.traits, char.avatar_url, char.greeting, examples_json, tags_json, char.id),
            )
            conn.commit()
            return char.id
        else:
            cur = conn.execute(
                """INSERT INTO characters (name, traits, avatar_url, greeting, examples, tags)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (char.name, char.traits, char.avatar_url, char.greeting, examples_json, tags_json),
            )
            conn.commit()
            return cur.lastrowid

    def _row_to_character(self, row) -> Character:
        return Character(
            id=row["id"],
            name=row["name"],
            traits=row["traits"],
            avatar_url=row["avatar_url"] or "",
            greeting=row["greeting"] or "",
            examples=self._list_from_json(row["examples"]),
            tags=self._list_from_json(row["tags"]),
        )

    def get_character(self, character_id: int) -> Optional[Character]:
        conn = self.connection
        row = conn.execute("SELECT * FROM characters WHERE id=?", (character_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_character(row)

    def list_characters(self) -> list[Character]:
        conn = self.connection
        rows = conn.execute("SELECT * FROM characters ORDER BY id DESC").fetchall()
        return [self._row_to_character(r) for r in rows]

    def delete_character(self, character_id: int):
        conn = self.connection
        conn.execute("DELETE FROM chat_sessions WHERE character_id=?", (character_id,))
        conn.execute("DELETE FROM characters WHERE id=?", (character_id,))
        conn.commit()

    def reset_all(self):
        """Wipe every character, session and stored app-state key."""
        conn = self.connection
        conn.execute("DELETE FROM chat_sessions")
        conn.execute("DELETE FROM characters")
        conn.execute("DELETE FROM app_state")
        conn.commit()

    # ── Chat Sessions ───────────────────────────────────────────

    def _derive_title(self, session: ChatSession) -> str:
        """Derive a short title from the first user message."""
        for m in session.messages:
            if m.role == "user":
                return m.content[:40] + ("..." if len(m.content) > 40 else "")
        if session.character_name:
            return session.character_name
        from ..i18n import t
        return t("new_chat")

    def save_session(self, session: ChatSession) -> int:
        """Upsert a session. Returns its id."""
        conn = self.connection
        messages_json = json.dumps(
            [m.to_dict() for m in session.messages],
            ensure_ascii=False,
        )
        title = self._derive_title(session) or session.title or ""
        if session.id:
            conn.execute(
                """UPDATE chat_sessions
                   SET character_id=?, character_name=?, title=?, messages=?, updated_at=datetime('now')
                   WHERE id=?""",
                (session.character_id, session.character_name, title, messages_json, session.id),
            )
            conn.commit()
            return session.id
        else:
            cur = conn.execute(
                """INSERT INTO chat_sessions (character_id, character_name, title, messages)
                   VALUES (?, ?, ?, ?)""",
                (session.character_id, session.character_name, title, messages_json),
            )
            conn.commit()
            sid = cur.lastrowid
            session.id = sid
            return sid

    def get_session(self, session_id: int) -> Optional[ChatSession]:
        conn = self.connection
        row = conn.execute("SELECT * FROM chat_sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            return None
        return ChatSession(
            id=row["id"],
            character_id=row["character_id"],
            character_name=row["character_name"] or "",
            messages=self._messages_from_json(row["messages"]),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    def list_sessions(self, character_id: Optional[int] = None) -> list[ChatSession]:
        conn = self.connection
        if character_id is not None:
            rows = conn.execute(
                "SELECT * FROM chat_sessions WHERE character_id=? ORDER BY updated_at DESC",
                (character_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_sessions ORDER BY updated_at DESC"
            ).fetchall()

        results = []
        for r in rows:
            results.append(ChatSession(
                id=r["id"],
                character_id=r["character_id"],
                character_name=r["character_name"] or "",
                messages=self._messages_from_json(r["messages"]),
                created_at=r["created_at"] or "",
                updated_at=r["updated_at"] or "",
            ))
        return results

    def delete_session(self, session_id: int):
        conn = self.connection
        conn.execute("DELETE FROM chat_sessions WHERE id=?", (session_id,))
        conn.commit()

    def delete_sessions_for_character(self, character_id: int):
        conn = self.connection
        conn.execute("DELETE FROM chat_sessions WHERE character_id=?", (character_id,))
        conn.commit()

    # ── Search ───────────────────────────────────────────────────

    def search_messages(self, query: str, character_id: Optional[int] = None) -> list[dict]:
        """Return matching snippets across all sessions.
        Each result: {"session_id": int, "character_name": str, "role": str, "content": str, "timestamp": str}
        """
        conn = self.connection
        sessions = self.list_sessions(character_id)
        results = []
        q = query.lower()
        for s in sessions:
            for m in s.messages:
                if q in m.content.lower():
                    results.append({
                        "session_id": s.id,
                        "character_name": s.character_name,
                        "role": m.role,
                        "content": m.content[:200] + ("..." if len(m.content) > 200 else ""),
                        "timestamp": m.timestamp,
                    })
        return results


# Global storage instance
storage = Storage()
