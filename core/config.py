"""Person AI Web — paths, models, providers and API key handling.

Key priority: key saved in the app (data/settings.json) > OS environment > .env file.
Keys saved in the app are base64-obfuscated (NOT encryption — local convenience only),
same format as the original Flet app, so an old settings.json can be reused as-is.
"""

import base64
import json
import os
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("PAI_DATA_DIR") or os.path.join(ROOT, "data")
STATIC_DIR = os.path.join(ROOT, "static")
DB_PATH = os.path.join(DATA_DIR, "person_ai.db")
KEYS_FILE = os.path.join(DATA_DIR, "settings.json")
ENV_FILE = os.path.join(ROOT, ".env")

os.makedirs(DATA_DIR, exist_ok=True)

# Where the old Flet app may have left its data (used once, on first start).
LEGACY_DIRS = [
    os.path.join(ROOT, "..", "person_ai", "storage", "data", ".person_ai"),
    os.path.join(os.path.expanduser("~"), ".person_ai"),
]

# ── Providers & models ────────────────────────────────────────
PROVIDERS = {
    "google": {
        "label": "Google Gemini",
        "env": "GOOGLE_API_KEY",
        "key_url": "https://aistudio.google.com/apikey",
    },
    "groq": {
        "label": "Groq",
        "env": "GROQ_API_KEY",
        "key_url": "https://console.groq.com/keys",
    },
    "openrouter": {
        "label": "OpenRouter",
        "env": "OPENROUTER_API_KEY",
        "key_url": "https://openrouter.ai/settings/keys",
    },
    "deepseek": {
        "label": "DeepSeek",
        "env": "DEEPSEEK_API_KEY",
        "key_url": "https://platform.deepseek.com/api_keys",
    },
    "demonroute": {
        "label": "Demon Route",
        "env": "DEMONROUTE_API_KEY",
        "key_url": "https://demonroute.com/dashboard",
    },
}

# Same model list as the original app (label → provider/id).
MODELS = {
    "Gemini 2.5 Flash": {"provider": "google", "id": "gemini-2.5-flash"},
    "Groq: Qwen 3.8 27B": {"provider": "groq", "id": "qwen/qwen3.8-27b"},
    "Groq: GPT-OSS 120B": {"provider": "groq", "id": "openai/gpt-oss-120b"},
    "DeepSeek V3.2": {"provider": "deepseek", "id": "deepseek-chat"},
    "DeepSeek V4 Pro": {"provider": "openrouter", "id": "deepseek/deepseek-v4-pro"},
    "Nemotron 3 Ultra 550B": {"provider": "openrouter", "id": "nvidia/nemotron-3-ultra-550b-a55b:free"},
    "Demon Route: Euryale v2.3 70B": {"provider": "demonroute", "id": "Sao10K/L3.3-70B-Euryale-v2.3"},
    "Demon Route: Cydonia 24B v4.3 heretic": {"provider": "demonroute", "id": "coder3101/Cydonia-24B-v4.3-heretic-v4"},
    "Demon Route: PaintedFantasy 24B": {"provider": "demonroute", "id": "zerofata/MS3.2-PaintedFantasy-v4.1-24B"},
}

# i18n key of the badge shown next to each provider's models.
PROVIDER_BADGE = {
    "google": "badge_smart",
    "groq": "badge_fast",
    "openrouter": "badge_free",
    "deepseek": "badge_smart",
    "demonroute": "badge_smart",
    "ollama": "badge_local",
}

# ── Local models (Ollama) ─────────────────────────────────────
OLLAMA_URL = (os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
LOCAL_PREFIX = "Ollama: "
_ollama_cache = {"t": 0.0, "data": None}


def ollama_status(force: bool = False) -> dict:
    """Is Ollama running, and which chat models are installed? (cached for 5 s)"""
    now = time.time()
    if not force and _ollama_cache["data"] is not None and now - _ollama_cache["t"] < 5:
        return _ollama_cache["data"]
    data = {"running": False, "url": OLLAMA_URL, "models": []}
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=0.8) as r:
            tags = json.loads(r.read().decode("utf-8"))
        data["running"] = True
        for m in tags.get("models") or []:
            name = m.get("name") or m.get("model") or ""
            det = m.get("details") or {}
            fam = " ".join([det.get("family") or ""] + (det.get("families") or [])).lower()
            if not name or "embed" in name.lower() or "bert" in fam:
                continue  # embedding models can't chat
            data["models"].append({
                "name": name,
                "size_gb": round((m.get("size") or 0) / 1e9, 1),
                "params": det.get("parameter_size") or "",
                "quant": det.get("quantization_level") or "",
            })
    except Exception:
        pass
    _ollama_cache.update(t=now, data=data)
    return data


def local_models() -> dict:
    return {
        LOCAL_PREFIX + m["name"]: {"provider": "ollama", "id": m["name"], "meta": m}
        for m in ollama_status()["models"]
    }


def all_models() -> dict:
    return {**MODELS, **local_models()}


PROVIDER_URLS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "demonroute": "https://api.demonroute.com/v1/chat/completions",
}


# ── .env parsing (no python-dotenv dependency) ────────────────
def _read_env_file() -> dict:
    values = {}
    if not os.path.isfile(ENV_FILE):
        return values
    try:
        with open(ENV_FILE, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                values[k.strip()] = v
    except OSError:
        pass
    return values


_ENV = _read_env_file()
PAI_PUBLIC_HOST = os.environ.get("PAI_PUBLIC_HOST", _ENV.get("PAI_PUBLIC_HOST", "")).strip().lower()
PAI_ACCESS_TEAM = os.environ.get("PAI_ACCESS_TEAM", _ENV.get("PAI_ACCESS_TEAM", "")).strip()
PAI_ACCESS_AUD = os.environ.get("PAI_ACCESS_AUD", _ENV.get("PAI_ACCESS_AUD", "")).strip()
_lock = threading.Lock()


def _obfuscate(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8") if text else ""


def _deobfuscate(encoded: str) -> str:
    if not encoded:
        return ""
    try:
        return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _load_local() -> dict:
    if not os.path.isfile(KEYS_FILE):
        return {}
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_local(data: dict):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_key(provider: str) -> str:
    info = PROVIDERS.get(provider)
    if not info:
        return ""
    with _lock:
        local = _deobfuscate(_load_local().get(f"{provider}_api_key", ""))
    if local:
        return local
    return os.environ.get(info["env"], "") or _ENV.get(info["env"], "")


def key_source(provider: str) -> str:
    info = PROVIDERS[provider]
    with _lock:
        if _deobfuscate(_load_local().get(f"{provider}_api_key", "")):
            return "app"
    if os.environ.get(info["env"]) or _ENV.get(info["env"]):
        return "env"
    return ""


def set_key(provider: str, key: str):
    """Save (or, with an empty key, remove) the in-app key for a provider."""
    if provider not in PROVIDERS:
        raise ValueError(provider)
    with _lock:
        data = _load_local()
        name = f"{provider}_api_key"
        if key:
            data[name] = _obfuscate(key)
        else:
            data.pop(name, None)
        _save_local(data)


def key_status() -> dict:
    out = {}
    for p, info in PROVIDERS.items():
        k = get_key(p)
        out[p] = {
            "label": info["label"],
            "key_url": info["key_url"],
            "set": bool(k),
            "source": key_source(p) if k else "",
            "hint": ("…" + k[-4:]) if len(k) >= 8 else ("…" if k else ""),
        }
    return out


def usable_models() -> list:
    cloud = [label for label, m in MODELS.items() if get_key(m["provider"])]
    return cloud + list(local_models())


def models_payload() -> list:
    usable = set(usable_models())
    out = []
    for label, m in all_models().items():
        local = m["provider"] == "ollama"
        meta = m.get("meta") or {}
        size = f"{meta['size_gb']} GB" if meta.get("size_gb") else ""
        out.append({
            "label": label,
            "provider": m["provider"],
            "provider_label": "Ollama" if local else PROVIDERS[m["provider"]]["label"],
            "id": m["id"],
            "badge": ("badge_free" if m["id"].endswith(":free")
                      else "badge_smart" if m["provider"] == "openrouter"
                      else PROVIDER_BADGE.get(m["provider"], "")),
            "available": label in usable,
            "local": local,
            "detail": " · ".join(x for x in (meta.get("params"), meta.get("quant"), size) if x),
        })
    return out
