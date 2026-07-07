"""Person AI - Central application state.

Replaces closure variables scattered across main.py.
All UI screens read/write state through this singleton.
"""

from dataclasses import dataclass, field
from typing import Optional

from ..models.character import Character
from ..models.chat_session import ChatSession, Message
from ..config import AVAILABLE_MODELS
from ..theme import get_theme


@dataclass
class AppState:
    """Central state container shared across all UI screens."""

    # ── Active character ───────────────────────────────────────
    character: Character = field(default_factory=Character)

    # ── Active chat session ────────────────────────────────────
    session: ChatSession = field(default_factory=ChatSession)
    streaming_active: bool = False
    streaming_cancel: bool = False

    # ── Settings (current UI state) ────────────────────────────
    selected_model: str = ""
    temperature: float = 1.4
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    max_tokens: int = 2048
    memory_size: int = 20

    # ── Model availability ─────────────────────────────────────
    usable_models: list[str] = field(default_factory=list)

    # ── Character image (URL) ──────────────────────────────────
    avatar_url: str = ""

    # ── Display / personalization ──────────────────────────────
    chat_background_url: str = ""   # URL for chat area background image
    user_name: str = ""             # Optional display name (fallback: "Sen")
    user_avatar_url: str = ""       # Optional user avatar URL
    user_persona: str = ""          # Optional: who the user is / standing requests for the AI

    # ── UI callbacks (set by chat_screen, read by chat_bubble) ──
    # Stored here instead of on page because ft.Page rejects arbitrary attributes in web mode.
    _cb_edit: object = None
    _cb_delete: object = None
    _cb_regenerate: object = None

    # ── Theme ─────────────────────────────────────────────────
    theme_mode: str = "dark"  # "dark" | "light" | "system"
    accent_color: str = ""  # custom accent override ("" = palette default)
    language: str = "tr"  # "tr" | "en"
    theme: dict = field(default_factory=lambda: get_theme("dark"))

    # ── UI memory (not persisted) ──────────────────────────────
    settings_section: str = "model"  # last active settings section

    def __post_init__(self):
        if self.session.character_name:
            self.character.name = self.session.character_name

    # ── Helpers ────────────────────────────────────────────────

    def add_user_message(self, text: str):
        self.session.add(Message(role="user", content=text))
        self._auto_save()

    def add_assistant_message(self, text: str):
        self.session.add(Message(role="assistant", content=text))
        self._auto_save()

    def _auto_save(self):
        """Save active session to DB after each message."""
        try:
            from ..services.storage import storage
            sid = storage.save_session(self.session)
            self.session.id = sid
            storage.set_last_active_session(sid)
            if self.session.character_id:
                storage.set_state(
                    f"last_character_{self.session.character_id}",
                    str(self.session.character_id),
                )
        except Exception:
            # Don't break the chat flow, but leave a trace for debugging
            import logging
            logging.getLogger("person_ai.state").warning(
                "Auto-save failed", exc_info=True
            )

    def load_session(self, session_id: int):
        """Load a saved session into active state."""
        from ..services.storage import storage
        saved = storage.get_session(session_id)
        if saved:
            self.session = saved
            self.character.name = saved.character_name
            if saved.character_id:
                char = storage.get_character(saved.character_id)
                if char:
                    self.character = char
                    self.avatar_url = char.avatar_url
            return True
        return False

    def load_last_or_create(self):
        """On startup: try to load last active session, fallback to fresh."""
        from ..services.storage import storage
        last_id = storage.last_active_session_id()
        if last_id:
            return self.load_session(last_id)
        return False

    # ── Settings persistence ───────────────────────────────────

    def refresh_theme(self):
        """Rebuild the theme dict from theme_mode + accent_color."""
        self.theme = get_theme(self.theme_mode, self.accent_color)

    def load_persisted_settings(self):
        """On startup: restore all persisted settings from the DB."""
        try:
            from ..services.storage import storage

            def _f(key: str, default: float) -> float:
                try:
                    return float(storage.get_state(key, str(default)))
                except (TypeError, ValueError):
                    return default

            # Appearance
            lang = storage.get_state("language", self.language)
            if lang in ("tr", "en"):
                self.language = lang
            mode = storage.get_state("theme_mode", self.theme_mode)
            if mode in ("dark", "light", "system"):
                self.theme_mode = mode
            self.accent_color = storage.get_state("accent_color", self.accent_color)
            self.refresh_theme()

            # Model & parameters
            self.selected_model = storage.get_state("selected_model", self.selected_model)
            self.temperature = _f("temperature", self.temperature)
            self.top_p = _f("top_p", self.top_p)
            self.frequency_penalty = _f("frequency_penalty", self.frequency_penalty)
            self.max_tokens = int(_f("max_tokens", self.max_tokens))
            self.memory_size = int(_f("memory_size", self.memory_size))

            # Display / personalization
            self.chat_background_url = storage.get_state("chat_background_url", "")
            self.user_name = storage.get_state("user_name", "")
            self.user_avatar_url = storage.get_state("user_avatar_url", "")
            self.user_persona = storage.get_state("user_persona", "")
        except Exception:
            pass  # Never block startup on settings load

    def save_persisted_settings(self):
        """Persist all user settings to the DB."""
        try:
            from ..services.storage import storage
            storage.set_state("language", self.language)
            storage.set_state("theme_mode", self.theme_mode)
            storage.set_state("accent_color", self.accent_color)
            storage.set_state("selected_model", self.selected_model)
            storage.set_state("temperature", str(self.temperature))
            storage.set_state("top_p", str(self.top_p))
            storage.set_state("frequency_penalty", str(self.frequency_penalty))
            storage.set_state("max_tokens", str(self.max_tokens))
            storage.set_state("memory_size", str(self.memory_size))
            storage.set_state("chat_background_url", self.chat_background_url)
            storage.set_state("user_name", self.user_name)
            storage.set_state("user_avatar_url", self.user_avatar_url)
            storage.set_state("user_persona", self.user_persona)
        except Exception:
            pass

    # Backward-compatible alias (older call sites)
    def save_display_settings(self):
        self.save_persisted_settings()

    @property
    def recent_messages(self) -> list[Message]:
        return self.session.recent_messages(self.memory_size)

    @property
    def system_instruction(self) -> str:
        return self.character.system_instruction

    @property
    def effective_system_instruction(self) -> str:
        """Character prompt + optional info about the user, if provided."""
        base = self.character.system_instruction
        extras = []
        name = (self.user_name or "").strip()
        persona = (self.user_persona or "").strip()
        if name:
            extras.append(
                f"The user you are talking to is named '{name}'. "
                f"Address them by this name when it feels natural."
            )
        if persona:
            extras.append(
                "Here is information the user shared about themselves and how "
                "they want you to treat them. Keep it in mind and adapt to it, "
                "but never read it back verbatim:\n" + persona
            )
        if extras:
            base += "\n\n--- ABOUT THE USER ---\n" + "\n".join(extras)
        return base

    @property
    def model_info(self) -> dict:
        return AVAILABLE_MODELS.get(self.selected_model, {})

    @property
    def provider(self) -> str:
        return self.model_info.get("provider", "")

    @property
    def model_id(self) -> str:
        return self.model_info.get("id", "")

    def apply_settings(self, character: Character, model: str, temperature: float, memory: int, avatar_url: str):
        """Apply settings from settings screen to state."""
        self.character = character
        self.session.character_name = character.name
        self.session.character_id = character.id
        self.selected_model = model
        self.temperature = temperature
        self.memory_size = memory
        self.avatar_url = avatar_url

    def clear_chat(self):
        """Clear current session messages only."""
        self.session.clear()
        self.streaming_cancel = True


# Global singleton
state = AppState()
