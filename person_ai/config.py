"""Person AI - Configuration & Constants

Loads environment variables via python-dotenv.
Defines available AI models and shared constants.
Supports local key storage with simple obfuscation.
"""

import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

def _writable_data_dir() -> str:
    """Return a writable directory that survives app updates.

    On Android/iOS the app bundle (next to this file) is READ-ONLY, so we must
    use the directory Flet pre-creates and exposes via FLET_APP_STORAGE_DATA.
    On desktop/Oracle that variable is usually unset, so we fall back to the
    user's home directory, and finally to the module directory for local dev.
    """
    base = (
        os.getenv("FLET_APP_STORAGE_DATA")
        or os.path.expanduser("~")
        or os.path.dirname(__file__)
    )
    target = os.path.join(base, ".person_ai")
    try:
        os.makedirs(target, exist_ok=True)
        return target
    except OSError:
        # Last-resort fallback: temp dir (always writable)
        import tempfile
        target = os.path.join(tempfile.gettempdir(), "person_ai")
        os.makedirs(target, exist_ok=True)
        return target


_SETTINGS_DIR = _writable_data_dir()
_SETTINGS_FILE = os.path.join(_SETTINGS_DIR, "settings.json")


def _obfuscate(text: str) -> str:
    """Simple base64 obfuscation (NOT encryption — local convenience only)."""
    if not text:
        return ""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _deobfuscate(encoded: str) -> str:
    """Reverse base64 obfuscation."""
    if not encoded:
        return ""
    try:
        return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _load_local_settings() -> dict:
    """Load settings from the local settings file."""
    if not os.path.isfile(_SETTINGS_FILE):
        return {}
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_local_settings(data: dict):
    """Save settings to the local settings file."""
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_local = _load_local_settings()

# ── API Keys (priority: env > local settings) ────────────────
def _get_key(env_name: str, local_name: str) -> str:
    env_val = os.environ.get(env_name, "")
    if env_val:
        return env_val
    encoded = _local.get(local_name, "")
    return _deobfuscate(encoded)


GOOGLE_API_KEY = _get_key("GOOGLE_API_KEY", "google_api_key")
GROQ_API_KEY = _get_key("GROQ_API_KEY", "groq_api_key")
OPENROUTER_API_KEY = _get_key("OPENROUTER_API_KEY", "openrouter_api_key")
DEEPSEEK_API_KEY = _get_key("DEEPSEEK_API_KEY", "deepseek_api_key")


def set_api_key(provider: str, key: str):
    """Save an API key locally and update the module-level variable."""
    global GOOGLE_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, DEEPSEEK_API_KEY
    local_name = f"{provider}_api_key"
    _local[local_name] = _obfuscate(key)
    _save_local_settings(_local)

    if provider == "google":
        GOOGLE_API_KEY = key
    elif provider == "groq":
        GROQ_API_KEY = key
    elif provider == "openrouter":
        OPENROUTER_API_KEY = key
    elif provider == "deepseek":
        DEEPSEEK_API_KEY = key

    # Refresh PROVIDER_KEYS
    PROVIDER_KEYS["openrouter"] = OPENROUTER_API_KEY
    PROVIDER_KEYS["deepseek"] = DEEPSEEK_API_KEY

    # Re-init clients (HTTP-based, no SDK needed)
    import person_ai.services.ai_providers as mod
    if provider == "google":
        mod.google_client = key  # truthy if key exists
    elif provider == "groq":
        mod.groq_client = key  # truthy if key exists

# ── Available Models ─────────────────────────────────────────
AVAILABLE_MODELS = {
    # -- Google Gemini (SDK) --
    "Gemini 2.5 Flash": {"provider": "google", "id": "gemini-2.5-flash"},

    # -- Groq (SDK - ultra fast) --
    "Groq: Llama 3.3 70B": {"provider": "groq", "id": "llama-3.3-70b-versatile"},

    # -- DeepSeek (HTTP) --
    "DeepSeek V3.2": {"provider": "deepseek", "id": "deepseek-chat"},

    # -- OpenRouter (HTTP) --
    "DeepSeek V4 Pro": {"provider": "openrouter", "id": "deepseek/deepseek-v4-pro"},
}

# ── Provider API endpoints ───────────────────────────────────
PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
}

# ── Provider auth keys map ───────────────────────────────────
PROVIDER_KEYS = {
    "openrouter": OPENROUTER_API_KEY,
    "deepseek": DEEPSEEK_API_KEY,
}

# ── Paths ────────────────────────────────────────────────────
DB_PATH = os.path.join(_SETTINGS_DIR, "person_ai.db")


def get_usable_models():
    """Return only models whose required API key is set."""
    from .services.ai_providers import google_client, groq_client

    usable = []
    for label, data in AVAILABLE_MODELS.items():
        provider = data["provider"]
        if provider == "google" and google_client:
            usable.append(label)
        elif provider == "groq" and groq_client:
            usable.append(label)
        elif provider in ("openrouter", "deepseek") and PROVIDER_KEYS.get(provider):
            usable.append(label)
    return usable


# ── Model metadata (provider icons, badge i18n keys) ─────────
# "badge" holds an i18n key — resolve with t(badge) at render time.
MODEL_META = {
    "google": {"icon": "AUTO_AWESOME", "badge": "badge_smart"},
    "groq": {"icon": "FLASH_ON", "badge": "badge_fast"},
    "openrouter": {"icon": "LANGUAGE", "badge": "badge_free"},
    "deepseek": {"icon": "GENETICS", "badge": "badge_smart"},
}


def _get_model_provider(label: str) -> str:
    return AVAILABLE_MODELS.get(label, {}).get("provider", "")
