"""Person AI Web — local server (Python standard library only).

Run:  python server.py          → http://127.0.0.1:8550
      python server.py --port 9000 --no-browser
"""

import argparse
import ipaddress
import json
import mimetypes
import os
import re
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import config  # noqa: E402
from core.access import AccessUnavailable, AccessValidator, InvalidToken  # noqa: E402
from core.providers import ProviderError, ProviderRateLimit, stream_chat  # noqa: E402
from core.storage import Storage  # noqa: E402

if config.PAI_PUBLIC_HOST and not (config.PAI_ACCESS_TEAM and config.PAI_ACCESS_AUD):
    raise SystemExit("Uzak erisim icin PAI_ACCESS_TEAM ve PAI_ACCESS_AUD gerekli.")

access = AccessValidator(config.PAI_ACCESS_TEAM, config.PAI_ACCESS_AUD)
db = Storage()
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")

MAX_BODY = 25 * 1024 * 1024  # avatars / backgrounds can be data URLs


# ── domain helpers ───────────────────────────────────────────
DEFAULT_RULES = (
    'Rules for this conversation:\n'
    "1. Stay in character. Speak and act as your character would, and don't step out of the story to talk about being an AI unless the user asks.\n"
    '2. Write vivid, natural roleplay: actions in *asterisks*, dialogue in plain text, with pacing and tone that fit the character and the scene.\n'
    "3. Play only your own character. Never write the user's dialogue, thoughts or actions, and never decide what the user does. End your reply where the user can respond.\n"
    '4. Reply in the language the user writes in.\n'
)


def system_instruction(char: dict, settings: dict, memory: dict | None = None) -> str:
    """Character persona prompt + optional info about the user (same text as the original app)."""
    base = (
        f"You are now acting entirely as a persona named {char['name']}. "
        f"Your core traits and background are: {char['traits']}.\n"
    )
    rules = DEFAULT_RULES
    try:
        with open(os.path.join(config.DATA_DIR, "system_prompt.txt"), encoding="utf-8") as file:
            override = file.read()
        if override.strip():
            rules = override if override.endswith("\n") else override + "\n"
    except (OSError, UnicodeError):
        pass
    base += rules
    if char.get("scenario"):
        base += f"\nCurrent scenario: {char['scenario']}\n"
    if char.get("examples"):
        base += (
            "\nExample dialogue snippets for your reference (match this tone/voice):\n"
            + "\n".join(f"- {ex}" for ex in char["examples"])
        )
    extras = []
    name = (settings.get("user_name") or "").strip()
    persona = (settings.get("user_persona") or "").strip()
    if name:
        extras.append(
            f"The user you are talking to is named '{name}'. "
            "Address them by this name when it feels natural."
        )
    if persona:
        extras.append(
            "Here is information the user shared about themselves and how "
            "they want you to treat them. Keep it in mind and adapt to it, "
            "but never read it back verbatim:\n" + persona
        )
    if extras:
        base += "\n\n--- ABOUT THE USER ---\n" + "\n".join(extras)
    if memory and (memory.get("summary") or memory.get("notes")):
        parts = []
        if memory.get("summary"):
            parts.append("Summary of earlier events in this conversation (older messages are no "
                         "longer shown to you; treat this as what already happened):\n" + memory["summary"])
        if memory.get("notes"):
            parts.append("Pinned facts you must always remember:\n" + memory["notes"])
        base += "\n\n--- MEMORY ---\n" + "\n\n".join(parts)
    return base


SUMMARY_PROMPT = (
    "You maintain the long-term memory of an ongoing roleplay chat between {user} and {char}. "
    "Update the running summary with the new messages below. Keep it as concise bullet points (max ~220 words): "
    "key events in order, facts learned about each character, relationship state, promises, open threads, "
    "current location/situation. Do not add commentary, warnings or anything that did not happen. "
    "Write in the same language the conversation uses. Output only the updated summary."
)


def summarize_session(store, sid: int, full: bool = False) -> dict:
    """Fold messages that left the context window into the session's running summary."""
    s = store.get_session(sid)
    if not s:
        raise ValueError("session not found")
    settings = store.get_settings()
    msgs = s["messages"]
    window = int(settings["memory_size"])
    cutoff = max(0, len(msgs) - window)
    mem = s["memory"]
    start, summary = (0, "") if full else (min(mem["summary_upto"], cutoff), mem["summary"])
    if cutoff - start < (1 if full else 6):
        return {"memory": mem, "changed": False}
    model = resolve_model(store, settings)
    if not model or (model.startswith(config.LOCAL_PREFIX) and model not in config.usable_models()):
        raise ProviderError("no usable model")
    char = store.get_character(s["character_id"]) or {"name": s["character_name"] or "Character"}
    user = (settings.get("user_name") or "").strip() or "User"
    system = SUMMARY_PROMPT.format(user=user, char=char["name"])
    params = {"temperature": 0.3, "top_p": 0.9, "frequency_penalty": 0.0, "max_tokens": 700,
              "num_ctx": settings["local_num_ctx"]}
    pos = start
    while pos < cutoff:  # batches keep the request small enough for 8K local models
        batch = msgs[pos:min(cutoff, pos + 30)]
        transcript = "\n".join(
            f"{user if m['role'] == 'user' else char['name']}: {m['content']}" for m in batch
        )
        prompt = (f"Current summary:\n{summary or '(empty)'}\n\nNew messages:\n{transcript}\n\n"
                  "Updated summary:")
        out = "".join(stream_chat(model, [{"role": "user", "content": prompt}], system, params)).strip()
        if out:
            summary = out
        pos += len(batch)
    mem = store.set_memory(sid, {"summary": summary, "summary_upto": cutoff})
    return {"memory": mem, "changed": True}


def resolve_model(store, settings: dict) -> str:
    usable = config.usable_models()
    sel = settings.get("selected_model") or ""
    if sel in usable:
        return sel
    if sel.startswith(config.LOCAL_PREFIX):
        return sel  # keep a local choice while Ollama is off; never switch to the cloud silently
    if usable:
        store.update_settings({"selected_model": usable[0]})
        return usable[0]
    return ""


def characters_with_meta(store) -> list:
    sessions = store.list_sessions()
    out = []
    for c in store.list_characters():
        own = [s for s in sessions if s["character_id"] == c["id"]]
        c["session_count"] = len(own)
        c["message_count"] = sum(s["message_count"] for s in own)
        c["last_session"] = (
            {"id": own[0]["id"], "preview": own[0]["preview"], "updated_at": own[0]["updated_at"]}
            if own else None
        )
        out.append(c)
    return out


def bootstrap(store, user: dict) -> dict:
    first = store.ensure_character()
    settings = store.get_settings()
    resolve_model(store, settings)
    settings = store.get_settings()
    active = store.last_active_session()
    if active and not store.get_character(active["character_id"]):
        active = None
    char_id = active["character_id"] if active else first["id"]
    if not active:
        recent = store.list_sessions()
        recent = [s for s in recent if store.get_character(s["character_id"])]
        if recent:
            char_id = recent[0]["character_id"]
    return {
        "settings": settings,
        "models": config.models_payload(),
        "ollama": config.ollama_status(),
        "keys": config.key_status(),
        "characters": characters_with_meta(store),
        "sessions": store.list_sessions(),
        "active": {"session": active, "character_id": char_id},
        "account": public_user(user),
    }


# ── accounts ─────────────────────────────────────────────────
COOKIE = "pai_session"
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
_attempts: dict = {}
_attempts_lock = threading.Lock()


def public_user(user: dict | None) -> dict | None:
    return {"id": user["id"], "username": user["username"], "created_at": user["created_at"]} if user else None


def rate_limited(key: str, limit: int = 8, window: int = 900) -> bool:
    """True when `key` already failed `limit` times in the last `window` seconds."""
    now = time.time()
    with _attempts_lock:
        hits = [t for t in _attempts.get(key, []) if now - t < window]
        _attempts[key] = hits
        return len(hits) >= limit


def note_failure(key: str):
    with _attempts_lock:
        _attempts.setdefault(key, []).append(time.time())


# ── HTTP handler ─────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    server_version = "PersonAI/3.0"

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in (self.path or "") and not self.path.startswith("/api/generate"):
            return
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    # ── responses ──
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if getattr(self, "_pending_cookie", None):
            self.send_header("Set-Cookie", self._pending_cookie)
            self._pending_cookie = None
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, msg):
        self._json({"error": msg}, status)

    def _cookie_token(self) -> str:
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE:
                return v
        return ""

    def _set_cookie(self, token: str):
        age = 0 if not token else 30 * 86400
        self._pending_cookie = f"{COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={age}"
        if self._via_tunnel():
            self._pending_cookie += "; Secure"

    def _host(self):
        try:
            return urlparse("//" + (self.headers.get("Host") or "")).hostname
        except ValueError:
            return None

    def _via_tunnel(self) -> bool:
        return bool(config.PAI_PUBLIC_HOST and self._host() == config.PAI_PUBLIC_HOST) or any(
            name in self.headers for name in
            ("Cf-Connecting-Ip", "Cf-Ray", "Cf-Visitor", "Cf-Access-Jwt-Assertion")
        )

    def _from_this_computer(self) -> bool:
        try:
            return (ipaddress.ip_address(self.client_address[0]).is_loopback
                    and not self._via_tunnel() and self._host() in {"127.0.0.1", "localhost", "::1"})
        except ValueError:
            return False

    def _client_ip(self):
        if self._via_tunnel() and getattr(self, "_access_validated", False):
            try:
                return str(ipaddress.ip_address(self.headers.get("Cf-Connecting-Ip", "")))
            except ValueError:
                pass
        return self.client_address[0]

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        if n > MAX_BODY:
            raise ValueError("body too large")
        raw = self.rfile.read(n)
        data = json.loads(raw.decode("utf-8") or "{}")
        return data if isinstance(data, dict) else {}

    def _local_only(self) -> bool:
        self._access_validated = False
        if self._via_tunnel():
            if not config.PAI_PUBLIC_HOST:
                self._error(403, "access denied")
                return False
            try:
                access.validate(self.headers.get("Cf-Access-Jwt-Assertion", ""))
            except InvalidToken:
                self._error(403, "access denied")
                return False
            except AccessUnavailable:
                self._error(503, "access unavailable")
                return False
            self._access_validated = True
        host = self._host()
        allowed_hosts = {"127.0.0.1", "localhost", "::1"}
        if config.PAI_PUBLIC_HOST:
            allowed_hosts.add(config.PAI_PUBLIC_HOST)
        if getattr(self.server, "allow_lan", False):
            peer = ipaddress.ip_address(self.client_address[0])
            if not (peer.is_private or peer.is_loopback):
                self._error(403, "local network access only")
                return False
            allowed_hosts.add(self.connection.getsockname()[0])
        if host not in allowed_hosts:
            self._error(403, "local access only")
            return False
        return True

    # ── static files ──
    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(config.STATIC_DIR, path.lstrip("/")))
        if not full.startswith(os.path.normpath(config.STATIC_DIR)) or not os.path.isfile(full):
            full = os.path.join(config.STATIC_DIR, "index.html")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    # ── routing ──
    ROUTES = [
        ("GET", r"/api/auth/me$", "get_me"),
        ("POST", r"/api/auth/(register|login|reset|logout)$", "post_auth"),
        ("POST", r"/api/account/password$", "post_password"),
        ("POST", r"/api/account/rename$", "post_rename"),
        ("GET", r"/api/bootstrap$", "get_bootstrap"),
        ("PATCH", r"/api/settings$", "patch_settings"),
        ("PUT", r"/api/keys/(\w+)$", "put_key"),
        ("GET", r"/api/models$", "get_models"),
        ("GET", r"/api/characters$", "get_characters"),
        ("POST", r"/api/characters$", "post_character"),
        ("PUT", r"/api/characters/(\d+)$", "put_character"),
        ("DELETE", r"/api/characters/(\d+)$", "delete_character"),
        ("GET", r"/api/sessions$", "get_sessions"),
        ("POST", r"/api/sessions$", "post_session"),
        ("GET", r"/api/sessions/(\d+)$", "get_session"),
        ("PUT", r"/api/sessions/(\d+)$", "put_session"),
        ("DELETE", r"/api/sessions/(\d+)$", "delete_session"),
        ("PUT", r"/api/sessions/(\d+)/memory$", "put_memory"),
        ("POST", r"/api/sessions/(\d+)/summarize$", "post_summarize"),
        ("PUT", r"/api/characters/(\d+)/favorite$", "put_favorite"),
        ("GET", r"/api/search$", "get_search"),
        ("POST", r"/api/generate$", "post_generate"),
        ("GET", r"/api/export$", "get_export"),
        ("POST", r"/api/reset$", "post_reset"),
    ]

    def _dispatch(self, method):
        if not self._local_only():
            return
        url = urlparse(self.path)
        if not url.path.startswith("/api/"):
            if method == "GET":
                return self._static(url.path)
            return self._error(404, "not found")
        for m, pattern, name in self.ROUTES:
            if m != method:
                continue
            match = re.match(pattern, url.path)
            if match:
                try:
                    self.query = {k: v[0] for k, v in parse_qs(url.query).items()}
                    self.token = self._cookie_token()
                    self.user = db.user_for_token(self.token)
                    self.store = db.scoped(self.user["id"]) if self.user else None
                    if not self.user and not url.path.startswith("/api/auth/"):
                        return self._error(401, "login required")
                    return getattr(self, name)(*match.groups())
                except (ValueError, json.JSONDecodeError) as e:
                    return self._error(400, str(e))
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                except Exception as e:  # pragma: no cover
                    import traceback
                    traceback.print_exc()
                    return self._error(500, str(e))
        self._error(404, "not found")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    # ── endpoints ──
    def get_me(self):
        self._json({"account": public_user(self.user), "has_users": db.user_count() > 0,
                    "local": self._from_this_computer()})

    def post_auth(self, action):
        b = self._body()
        if action == "logout":
            db.end_auth_session(self.token)
            self._set_cookie("")
            return self._json({"ok": True})
        username = str(b.get("username") or "").strip().lower()
        password = str(b.get("password") or "")
        peer = self._client_ip()
        if not USERNAME_RE.match(username):
            return self._error(400, "bad_username")
        if not 4 <= len(password) <= 128:
            return self._error(400, "bad_password")
        if rate_limited(f"{action}|{peer}"):
            return self._error(429, "too_many")
        if action == "register":
            if db.find_user(username):
                return self._error(409, "username_taken")
            user = db.create_user(username, password)
        elif action == "reset":
            if not self._from_this_computer():
                return self._error(403, "reset_local_only")
            found = db.find_user(username)
            if not found:
                note_failure(f"{action}|{peer}")
                return self._error(404, "no_such_user")
            db.set_password(found["id"], password)
            db.end_other_sessions(found["id"])
            user = db.get_user(found["id"])
        else:
            user = db.check_password(username, password)
            if not user:
                note_failure(f"{action}|{peer}")
                return self._error(401, "wrong_login")
        self._set_cookie(db.create_auth_session(user["id"]))
        self._json({"account": public_user(user)})

    def post_password(self):
        b = self._body()
        current, new = str(b.get("current") or ""), str(b.get("password") or "")
        if not db.check_password(self.user["username"], current):
            note_failure(f"password|{self._client_ip()}")
            return self._error(400, "wrong_current")
        if not 4 <= len(new) <= 128:
            return self._error(400, "bad_password")
        db.set_password(self.user["id"], new)
        db.end_other_sessions(self.user["id"], self.token)  # sign out other devices
        self._json({"ok": True})

    def post_rename(self):
        username = str(self._body().get("username") or "").strip().lower()
        if not USERNAME_RE.match(username):
            return self._error(400, "bad_username")
        other = db.find_user(username)
        if other and other["id"] != self.user["id"]:
            return self._error(409, "username_taken")
        db.rename_user(self.user["id"], username)
        self._json({"account": public_user(db.get_user(self.user["id"]))})

    def get_bootstrap(self):
        self._json(bootstrap(self.store, self.user))

    def patch_settings(self):
        s = self.store.update_settings(self._body())
        self._json({"settings": s})

    def put_key(self, provider):
        if provider not in config.PROVIDERS:
            return self._error(404, "unknown provider")
        if not self._from_this_computer():
            return self._error(403, "keys_local_only")
        key = str(self._body().get("key") or "").strip()
        config.set_key(provider, key)
        resolve_model(self.store, self.store.get_settings())
        self._json({
            "keys": config.key_status(),
            "models": config.models_payload(),
            "settings": self.store.get_settings(),
        })

    def get_models(self):
        ollama = config.ollama_status(force=True)
        resolve_model(self.store, self.store.get_settings())
        self._json({"models": config.models_payload(), "ollama": ollama, "settings": self.store.get_settings()})

    def get_characters(self):
        self._json({"characters": characters_with_meta(self.store)})

    def post_character(self):
        c = self.store.save_character(self._body())
        self._json({"character": c, "characters": characters_with_meta(self.store)})

    def put_character(self, cid):
        if not self.store.get_character(int(cid)):
            return self._error(404, "character not found")
        c = self.store.save_character(self._body(), int(cid))
        if not c:
            return self._error(404, "character not found")
        self._json({"character": c, "characters": characters_with_meta(self.store)})

    def delete_character(self, cid):
        self.store.delete_character(int(cid))
        self._json({"ok": True})

    def get_sessions(self):
        cid = self.query.get("character_id")
        self._json({"sessions": self.store.list_sessions(int(cid) if cid else None)})

    def post_session(self):
        b = self._body()
        s = self.store.save_session(b.get("character_id"), b.get("messages") or [])
        self._json({"session": s})

    def get_session(self, sid):
        s = self.store.get_session(int(sid))
        if not s:
            return self._error(404, "session not found")
        self.store.set_state("last_active_session", sid)
        self._json({"session": s})

    def put_session(self, sid):
        b = self._body()
        s = self.store.save_session(b.get("character_id"), b.get("messages") or [], int(sid))
        self._json({"session": s})

    def delete_session(self, sid):
        self.store.delete_session(int(sid))
        self._json({"ok": True})

    def put_memory(self, sid):
        if not self.store.get_session(int(sid)):
            return self._error(404, "session not found")
        self._json({"memory": self.store.set_memory(int(sid), self._body())})

    def post_summarize(self, sid):
        full = bool(self._body().get("full"))
        try:
            self._json(summarize_session(self.store, int(sid), full))
        except ProviderError as e:
            self._json({"error": e.code, "detail": e.detail}, 502)

    def put_favorite(self, cid):
        self.store.set_favorite(int(cid), bool(self._body().get("favorite")))
        self._json({"characters": characters_with_meta(self.store)})

    def get_search(self):
        self._json({"results": self.store.search_messages(self.query.get("q", ""))})

    def get_export(self):
        body = json.dumps(self.store.export_all(), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="person_ai_export.json"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def post_reset(self):
        self.store.reset_all()
        self._json({"ok": True})

    # ── streaming generation (server-sent events) ──
    def post_generate(self):
        b = self._body()
        settings = self.store.get_settings()
        char = self.store.get_character(b.get("character_id")) or self.store.ensure_character()
        msgs = [
            {"role": m.get("role"), "content": str(m.get("content", ""))}
            for m in (b.get("messages") or [])
            if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()
        ]
        msgs = msgs[-int(settings["memory_size"]):]
        memory = self.store.get_memory(int(b["session_id"])) if b.get("session_id") else None
        system = system_instruction(char, settings, memory)
        params = {
            "temperature": settings["temperature"],
            "top_p": settings["top_p"],
            "frequency_penalty": settings["frequency_penalty"],
            "max_tokens": settings["max_tokens"],
            "num_ctx": settings["local_num_ctx"],
        }

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        closed = threading.Event()

        def send(obj):
            try:
                self.wfile.write(("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                closed.set()

        usable = config.usable_models()
        first = resolve_model(self.store, settings)
        if first.startswith(config.LOCAL_PREFIX) and first not in usable:
            return send({"t": "error", "code": "ollama_down"})
        if not usable:
            return send({"t": "error", "code": "no_key"})
        order = [first] + [m for m in usable if m != first]

        for i, label in enumerate(order):
            if i > 0:
                send({"t": "fallback", "model": label})
            started = False
            try:
                for chunk in stream_chat(label, msgs, system, params, cancel=closed.is_set):
                    started = True
                    send({"t": "token", "v": chunk})
                    if closed.is_set():
                        return
                if i > 0:
                    self.store.update_settings({"selected_model": label})
                return send({"t": "done", "model": label})
            except ProviderRateLimit as e:
                if started or closed.is_set():
                    return send({"t": "error", "code": e.code, "detail": e.detail})
                continue
            except ProviderError as e:
                return send({"t": "error", "code": e.code, "detail": e.detail})
            except Exception as e:  # pragma: no cover
                return send({"t": "error", "code": "unknown", "detail": str(e)})
        send({"t": "error", "code": "all_failed"})


def main():
    ap = argparse.ArgumentParser(description="Person AI (web)")
    ap.add_argument("--host", default="127.0.0.1", help="Dinlenecek adres (yerel ag icin: 0.0.0.0)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PAI_PORT", 8550)))
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.allow_lan = args.host not in ("127.0.0.1", "localhost", "::1")
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{args.port}"
    print(f"\n  Person AI calisiyor → {url}\n  Kapatmak icin bu pencerede Ctrl+C.\n")
    if args.host == "0.0.0.0":
        print(f"  Yerel ag erisimi acik. Diger cihazdan: http://<bu bilgisayarin yerel IP adresi>:{args.port}\n")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Kapatiliyor...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
