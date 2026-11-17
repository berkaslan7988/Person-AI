"""Person AI Web — SQLite storage (same schema as the original Flet app, plus accounts).

Tables: characters, chat_sessions (messages stored as a JSON list), app_state (key/value),
users, auth_sessions. `Storage.scoped(uid)` gives a view that only sees one account's data.
"""

import copy
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import threading
import time
from datetime import datetime

from .config import DB_PATH, KEYS_FILE, LEGACY_DIRS
from .starter_cards import STARTER_CHARACTERS

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

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pass_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

SESSION_DAYS = 30
PBKDF2_ROUNDS = 200_000


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# Persisted settings and their defaults (same keys as the original app).
SETTINGS_DEFAULTS = {
    "language": "tr",
    "theme_mode": "dark",
    "accent_color": "",
    "selected_model": "",
    "temperature": 1.4,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "max_tokens": 2048,
    "memory_size": 20,
    "local_num_ctx": 8192,
    "chat_background_url": "",
    "user_name": "",
    "user_avatar_url": "",
    "user_persona": "",
    "onboarding_seen": "",
}
_FLOAT_KEYS = {"temperature", "top_p", "frequency_penalty"}
_INT_KEYS = {"max_tokens", "memory_size", "local_num_ctx"}
_RANGES = {
    "temperature": (0.0, 2.0),
    "top_p": (0.0, 1.0),
    "frequency_penalty": (-2.0, 2.0),
    "max_tokens": (256, 8192),
    "memory_size": (4, 50),
    "local_num_ctx": (2048, 32768),
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _migrate_legacy():
    """First start only: copy the old Flet app's database and saved keys."""
    if os.path.exists(DB_PATH):
        return
    for d in LEGACY_DIRS:
        old_db = os.path.join(d, "person_ai.db")
        if os.path.isfile(old_db):
            try:
                src = sqlite3.connect(old_db)
                dst = sqlite3.connect(DB_PATH)
                src.backup(dst)  # includes pending WAL pages
                dst.close()
                src.close()
                print(f"[person_ai] Eski veritabani tasindi: {os.path.abspath(old_db)}")
            except sqlite3.Error as e:
                print(f"[person_ai] Eski veritabani tasinamadi: {e}")
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                continue
            old_keys = os.path.join(d, "settings.json")
            if os.path.isfile(old_keys) and not os.path.exists(KEYS_FILE):
                shutil.copyfile(old_keys, KEYS_FILE)
            break


class Storage:
    def __init__(self, path: str = DB_PATH):
        _migrate_legacy()
        self.uid = None  # None = unscoped (all data; used by the fine-tune scripts)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self._add_columns()
        self.conn.commit()

    def _add_columns(self):
        """Additive migrations (old databases keep working)."""
        wanted = {
            "characters": {
                "scenario": "TEXT DEFAULT ''",
                "alt_greetings": "TEXT DEFAULT '[]'",
                "favorite": "INTEGER DEFAULT 0",
            },
            "chat_sessions": {"memory": "TEXT DEFAULT '{}'", "user_id": "INTEGER"},
        }
        wanted["characters"]["user_id"] = "INTEGER"
        for table, cols in wanted.items():
            have = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols.items():
                if col not in have:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    # ── per-user scoping ───────────────────────────────────────
    def scoped(self, uid: int) -> "Storage":
        """A view of the same database that only sees one account's data."""
        view = copy.copy(self)
        view.uid = uid
        return view

    def _w(self) -> tuple:
        """SQL filter + params for the current account."""
        return ("user_id=?", (self.uid,)) if self.uid is not None else ("1=1", ())

    def _k(self, key: str) -> str:
        return f"u{self.uid}:{key}" if self.uid is not None else key

    # ── accounts ───────────────────────────────────────────────
    def user_count(self) -> int:
        with self._lock:
            return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def get_user(self, uid) -> dict | None:
        with self._lock:
            r = self.conn.execute("SELECT id, username, created_at FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None

    def find_user(self, username: str) -> dict | None:
        with self._lock:
            r = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(r) if r else None

    def create_user(self, username: str, password: str) -> dict:
        """Create an account. The very first account inherits the data made before accounts existed."""
        salt = secrets.token_hex(16)
        with self._lock:
            first = self.user_count() == 0
            cur = self.conn.execute(
                "INSERT INTO users (username, pass_hash, salt) VALUES (?, ?, ?)",
                (username, _hash_password(password, salt), salt),
            )
            uid = cur.lastrowid
            if first:
                self.conn.execute("UPDATE characters SET user_id=? WHERE user_id IS NULL", (uid,))
                self.conn.execute("UPDATE chat_sessions SET user_id=? WHERE user_id IS NULL", (uid,))
                for key in list(SETTINGS_DEFAULTS) + ["last_active_session"]:
                    row = self.conn.execute("SELECT value FROM app_state WHERE key=?", (key,)).fetchone()
                    if row is not None:
                        self.conn.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                                          (f"u{uid}:{key}", row["value"]))
            self.conn.commit()
        return self.get_user(uid)

    def check_password(self, username: str, password: str) -> dict | None:
        u = self.find_user(username)
        if not u:
            _hash_password(password, "timing-equaliser")  # same cost whether or not the user exists
            return None
        if hmac.compare_digest(u["pass_hash"], _hash_password(password, u["salt"])):
            return self.get_user(u["id"])
        return None

    def set_password(self, uid: int, password: str):
        salt = secrets.token_hex(16)
        with self._lock:
            self.conn.execute("UPDATE users SET pass_hash=?, salt=? WHERE id=?",
                              (_hash_password(password, salt), salt, uid))
            self.conn.commit()

    def rename_user(self, uid: int, username: str):
        with self._lock:
            self.conn.execute("UPDATE users SET username=? WHERE id=?", (username, uid))
            self.conn.commit()

    def create_auth_session(self, uid: int) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self.conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (int(time.time()),))
            self.conn.execute("INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                              (_token_hash(token), uid, int(time.time()) + SESSION_DAYS * 86400))
            self.conn.commit()
        return token

    def user_for_token(self, token: str) -> dict | None:
        if not token:
            return None
        with self._lock:
            r = self.conn.execute(
                "SELECT user_id FROM auth_sessions WHERE token_hash=? AND expires_at>=?",
                (_token_hash(token), int(time.time())),
            ).fetchone()
        return self.get_user(r["user_id"]) if r else None

    def end_auth_session(self, token: str):
        with self._lock:
            self.conn.execute("DELETE FROM auth_sessions WHERE token_hash=?", (_token_hash(token or ""),))
            self.conn.commit()

    def end_other_sessions(self, uid: int, keep_token: str = ""):
        with self._lock:
            self.conn.execute("DELETE FROM auth_sessions WHERE user_id=? AND token_hash<>?",
                              (uid, _token_hash(keep_token)))
            self.conn.commit()

    # ── helpers ────────────────────────────────────────────────
    @staticmethod
    def _list(raw) -> list:
        try:
            data = json.loads(raw or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @classmethod
    def _messages(cls, raw) -> list:
        out = []
        for m in cls._list(raw):
            if not isinstance(m, dict):
                continue
            role = m.get("role", "user")
            if role == "model":
                role = "assistant"
            if role not in ("user", "assistant"):
                continue
            msg = {
                "role": role,
                "content": str(m.get("content", "")),
                "timestamp": m.get("timestamp") or _now_iso(),
            }
            swipes = m.get("swipes")
            if role == "assistant" and isinstance(swipes, list) and len(swipes) > 1:
                swipes = [str(x) for x in swipes][:50]
                try:
                    idx = min(max(int(m.get("swipe", 0)), 0), len(swipes) - 1)
                except (TypeError, ValueError):
                    idx = 0
                swipes[idx] = msg["content"]  # content is always the visible swipe
                msg["swipes"] = swipes
                msg["swipe"] = idx
            out.append(msg)
        return out

    @staticmethod
    def _memory(raw) -> dict:
        try:
            m = json.loads(raw or "{}")
            m = m if isinstance(m, dict) else {}
        except (json.JSONDecodeError, TypeError):
            m = {}
        try:
            upto = max(0, int(m.get("summary_upto") or 0))
        except (TypeError, ValueError):
            upto = 0
        return {
            "summary": str(m.get("summary") or ""),
            "summary_upto": upto,
            "notes": str(m.get("notes") or ""),
            "updated_at": str(m.get("updated_at") or ""),
        }

    # ── app state / settings ───────────────────────────────────
    def get_state(self, key: str, default: str = "") -> str:
        with self._lock:
            row = self.conn.execute("SELECT value FROM app_state WHERE key=?", (self._k(key),)).fetchone()
        return row["value"] if row else default

    def set_state(self, key: str, value: str):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)", (self._k(key), str(value))
            )
            self.conn.commit()

    def get_settings(self) -> dict:
        out = {}
        for k, default in SETTINGS_DEFAULTS.items():
            raw = self.get_state(k, None)
            if raw is None:
                out[k] = default
                continue
            try:
                if k in _FLOAT_KEYS:
                    out[k] = float(raw)
                elif k in _INT_KEYS:
                    out[k] = int(float(raw))
                else:
                    out[k] = raw
            except (TypeError, ValueError):
                out[k] = default
        if out["language"] not in ("tr", "en"):
            out["language"] = "tr"
        if out["theme_mode"] not in ("dark", "light", "system"):
            out["theme_mode"] = "dark"
        return out

    def update_settings(self, patch: dict) -> dict:
        for k, v in patch.items():
            if k not in SETTINGS_DEFAULTS:
                continue
            if k in _FLOAT_KEYS or k in _INT_KEYS:
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    continue
                lo, hi = _RANGES[k]
                v = min(hi, max(lo, v))
                v = int(round(v)) if k in _INT_KEYS else round(v, 3)
            elif v is None:
                v = ""
            self.set_state(k, str(v))
        return self.get_settings()

    # ── characters ─────────────────────────────────────────────
    def _row_to_char(self, r) -> dict:
        return {
            "id": r["id"],
            "name": r["name"],
            "traits": r["traits"] or "",
            "avatar_url": r["avatar_url"] or "",
            "greeting": r["greeting"] or "",
            "examples": [str(x) for x in self._list(r["examples"])],
            "tags": [str(x) for x in self._list(r["tags"])],
            "scenario": r["scenario"] or "",
            "alt_greetings": [str(x) for x in self._list(r["alt_greetings"]) if str(x).strip()],
            "favorite": bool(r["favorite"]),
        }

    def list_characters(self) -> list:
        with self._lock:
            w, p = self._w()
            rows = self.conn.execute(f"SELECT * FROM characters WHERE {w} ORDER BY id DESC", p).fetchall()
        return [self._row_to_char(r) for r in rows]

    def get_character(self, cid) -> dict | None:
        if cid is None:
            return None
        with self._lock:
            w, p = self._w()
            r = self.conn.execute(f"SELECT * FROM characters WHERE id=? AND {w}", (cid, *p)).fetchone()
        return self._row_to_char(r) if r else None

    @staticmethod
    def _clean_char(data: dict) -> dict:
        def _strs(v):
            if isinstance(v, str):
                v = [x for x in v.split("\n")]
            return [str(x).strip() for x in (v or []) if str(x).strip()]
        return {
            "name": (str(data.get("name") or "").strip() or "Unnamed")[:120],
            "traits": str(data.get("traits") or "").strip(),
            "avatar_url": str(data.get("avatar_url") or "").strip(),
            "greeting": str(data.get("greeting") or "").strip(),
            "examples": _strs(data.get("examples")),
            "tags": _strs(data.get("tags")),
            "scenario": str(data.get("scenario") or "").strip(),
            "alt_greetings": [str(x).strip() for x in (data.get("alt_greetings") or []) if str(x).strip()],
            "favorite": 1 if data.get("favorite") else 0,
        }

    def save_character(self, data: dict, cid=None) -> dict:
        c = self._clean_char(data)
        ex = json.dumps(c["examples"], ensure_ascii=False)
        tags = json.dumps(c["tags"], ensure_ascii=False)
        alts = json.dumps(c["alt_greetings"], ensure_ascii=False)
        with self._lock:
            if cid and not self.get_character(cid):
                return None  # not this account's character
            if cid:
                self.conn.execute(
                    "UPDATE characters SET name=?, traits=?, avatar_url=?, greeting=?, examples=?, tags=?, "
                    "scenario=?, alt_greetings=?, favorite=? WHERE id=?",
                    (c["name"], c["traits"], c["avatar_url"], c["greeting"], ex, tags,
                     c["scenario"], alts, c["favorite"], cid),
                )
                # keep the denormalised name on sessions in sync
                self.conn.execute(
                    "UPDATE chat_sessions SET character_name=? WHERE character_id=?", (c["name"], cid)
                )
            else:
                cur = self.conn.execute(
                    "INSERT INTO characters (name, traits, avatar_url, greeting, examples, tags, scenario, "
                    "alt_greetings, favorite, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (c["name"], c["traits"], c["avatar_url"], c["greeting"], ex, tags,
                     c["scenario"], alts, c["favorite"], self.uid),
                )
                cid = cur.lastrowid
            self.conn.commit()
        return self.get_character(cid)

    def set_favorite(self, cid, value: bool):
        with self._lock:
            w, p = self._w()
            self.conn.execute(f"UPDATE characters SET favorite=? WHERE id=? AND {w}", (1 if value else 0, cid, *p))
            self.conn.commit()

    def delete_character(self, cid):
        with self._lock:
            if not self.get_character(cid):
                return
            self.conn.execute("DELETE FROM chat_sessions WHERE character_id=?", (cid,))
            self.conn.execute("DELETE FROM characters WHERE id=?", (cid,))
            self.conn.commit()

    def ensure_character(self) -> dict:
        """Make sure at least one character exists (seeds the starter cast)."""
        chars = self.list_characters()
        if chars:
            return chars[0]
        # newest-first listing: insert in reverse so the gallery shows them in landing order
        seeded = [self.save_character(c) for c in reversed(STARTER_CHARACTERS)]
        return seeded[-1]

    # ── sessions ───────────────────────────────────────────────
    @staticmethod
    def _derive_title(messages: list, character_name: str) -> str:
        for m in messages:
            if m["role"] == "user" and m["content"].strip():
                text = " ".join(m["content"].replace("*", "").replace("`", "").split())
                return text[:40] + ("..." if len(text) > 40 else "")
        return character_name or ""

    def _row_to_session(self, r, full=True) -> dict:
        msgs = self._messages(r["messages"])
        last_ai = ""
        for m in reversed(msgs):
            if m["role"] == "assistant":
                last_ai = m["content"]
                break
        last = msgs[-1]["content"] if msgs else ""
        s = {
            "id": r["id"],
            "character_id": r["character_id"],
            "character_name": r["character_name"] or "",
            "title": r["title"] or r["character_name"] or "",
            "message_count": len(msgs),
            "preview": " ".join(last.split())[:120],
            "last_ai_preview": " ".join(last_ai.split())[:160],
            "created_at": r["created_at"] or "",
            "updated_at": r["updated_at"] or "",
        }
        if full:
            s["messages"] = msgs
            s["memory"] = self._memory(r["memory"])
        return s

    def list_sessions(self, character_id=None) -> list:
        with self._lock:
            w, p = self._w()
            if character_id is not None:
                rows = self.conn.execute(
                    f"SELECT * FROM chat_sessions WHERE character_id=? AND {w} ORDER BY updated_at DESC, id DESC",
                    (character_id, *p),
                ).fetchall()
            else:
                rows = self.conn.execute(
                    f"SELECT * FROM chat_sessions WHERE {w} ORDER BY updated_at DESC, id DESC", p
                ).fetchall()
        return [self._row_to_session(r, full=False) for r in rows]

    def get_session(self, sid) -> dict | None:
        with self._lock:
            w, p = self._w()
            r = self.conn.execute(f"SELECT * FROM chat_sessions WHERE id=? AND {w}", (sid, *p)).fetchone()
        return self._row_to_session(r) if r else None

    def save_session(self, character_id, messages: list, sid=None) -> dict:
        msgs = self._messages(json.dumps(messages))
        char = self.get_character(character_id)
        if not char:
            character_id = None  # never attach a chat to another account's character
        cname = char["name"] if char else ""
        title = self._derive_title(msgs, cname)
        payload = json.dumps(msgs, ensure_ascii=False)
        with self._lock:
            if sid and self.get_session(sid):
                self.conn.execute(
                    "UPDATE chat_sessions SET character_id=?, character_name=?, title=?, messages=?, "
                    "updated_at=datetime('now') WHERE id=?",
                    (character_id, cname, title, payload, sid),
                )
            else:
                cur = self.conn.execute(
                    "INSERT INTO chat_sessions (character_id, character_name, title, messages, user_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (character_id, cname, title, payload, self.uid),
                )
                sid = cur.lastrowid
            self.conn.commit()
        self.set_state("last_active_session", str(sid))
        return self.get_session(sid)

    def get_memory(self, sid) -> dict:
        with self._lock:
            w, p = self._w()
            r = self.conn.execute(f"SELECT memory FROM chat_sessions WHERE id=? AND {w}", (sid, *p)).fetchone()
        return self._memory(r["memory"]) if r else self._memory("{}")

    def set_memory(self, sid, patch: dict) -> dict:
        if not self.get_session(sid):
            return self._memory("{}")
        mem = self.get_memory(sid)
        for k in ("summary", "notes"):
            if k in patch:
                mem[k] = str(patch[k] or "")
        if "summary_upto" in patch:
            mem["summary_upto"] = max(0, int(patch["summary_upto"] or 0))
        mem["updated_at"] = _now_iso()
        with self._lock:
            self.conn.execute(
                "UPDATE chat_sessions SET memory=? WHERE id=?", (json.dumps(mem, ensure_ascii=False), sid)
            )
            self.conn.commit()
        return mem

    def delete_session(self, sid):
        with self._lock:
            w, p = self._w()
            self.conn.execute(f"DELETE FROM chat_sessions WHERE id=? AND {w}", (sid, *p))
            self.conn.commit()

    def last_active_session(self) -> dict | None:
        raw = self.get_state("last_active_session", "")
        try:
            return self.get_session(int(raw)) if raw else None
        except ValueError:
            return None

    # ── search ─────────────────────────────────────────────────
    def search_messages(self, query: str, limit: int = 60) -> list:
        q = query.strip().lower()
        if not q:
            return []
        results = []
        with self._lock:
            w, p = self._w()
            rows = self.conn.execute(
                f"SELECT * FROM chat_sessions WHERE {w} ORDER BY updated_at DESC, id DESC", p
            ).fetchall()
        for r in rows:
            for i, m in enumerate(self._messages(r["messages"])):
                text = m["content"]
                pos = text.lower().find(q)
                if pos < 0:
                    continue
                start = max(0, pos - 60)
                snippet = ("…" if start else "") + text[start:pos + len(q) + 120]
                results.append({
                    "session_id": r["id"],
                    "character_id": r["character_id"],
                    "character_name": r["character_name"] or "",
                    "role": m["role"],
                    "index": i,
                    "snippet": " ".join(snippet.split()),
                    "timestamp": m["timestamp"],
                })
                if len(results) >= limit:
                    return results
        return results

    # ── data management ───────────────────────────────────────
    def export_all(self) -> dict:
        with self._lock:
            w, p = self._w()
            rows = self.conn.execute(f"SELECT * FROM chat_sessions WHERE {w} ORDER BY id", p).fetchall()
        settings = self.get_settings()
        return {
            "app": "Person AI",
            "exported_at": _now_iso(),
            "settings": settings,
            "characters": self.list_characters(),
            "sessions": [self._row_to_session(r) for r in rows],
        }

    def reset_all(self):
        """Wipe characters, sessions and state — but keep the user's settings."""
        keep = self.get_settings()
        with self._lock:
            w, p = self._w()
            self.conn.execute(f"DELETE FROM chat_sessions WHERE {w}", p)
            self.conn.execute(f"DELETE FROM characters WHERE {w}", p)
            if self.uid is not None:
                self.conn.execute("DELETE FROM app_state WHERE key LIKE ?", (f"u{self.uid}:%",))
            else:
                self.conn.execute("DELETE FROM app_state WHERE key NOT LIKE 'u%:%'")
            self.conn.commit()
        self.update_settings(keep)
