"""Person AI - Unified AI Provider abstraction (pure HTTP, no heavy SDKs).

Supports: Google Gemini, Groq, OpenRouter, DeepSeek — all via urllib.
"""

import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
import socket

from ..config import (
    GOOGLE_API_KEY, GROQ_API_KEY,
    PROVIDER_KEYS, PROVIDER_URLS,
)

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "Accept": "application/json",
}

# ── Typed Errors ───────────────────────────────────────────────

class ProviderError(Exception):
    user_message_key: str = "err_unknown"

    @property
    def user_message(self) -> str:
        """Localized, user-facing message (resolved lazily via i18n)."""
        from ..i18n import t
        return t(self.user_message_key)

class ProviderTimeoutError(ProviderError):
    user_message_key = "err_timeout"

class ProviderConnectionError(ProviderError):
    user_message_key = "err_connection"

class ProviderAuthError(ProviderError):
    user_message_key = "err_auth"

class ProviderRateLimitError(ProviderError):
    user_message_key = "err_rate_limit"

class ProviderContentFilterError(ProviderError):
    user_message_key = "err_content_filter"

class ProviderBadResponseError(ProviderError):
    user_message_key = "err_bad_response"


def _classify_error(exc: Exception, status_code: int = 0) -> ProviderError:
    if isinstance(exc, ProviderError):
        return exc
    msg = str(exc).lower()
    if isinstance(exc, (socket.timeout, TimeoutError, urllib.error.URLError)):
        if "timed out" in msg or "timeout" in msg:
            return ProviderTimeoutError(str(exc))
        return ProviderConnectionError(str(exc))
    if status_code == 401 or status_code == 403:
        return ProviderAuthError(str(exc))
    if status_code == 429:
        return ProviderRateLimitError(str(exc))
    if "429" in msg or "resource_exhausted" in msg or "rate limit" in msg:
        return ProviderRateLimitError(str(exc))
    if "safety" in msg or "content_filter" in msg or "blocked" in msg:
        return ProviderContentFilterError(str(exc))
    return ProviderError(str(exc))


def http_post(url: str, headers: dict, payload: dict, timeout: int = 120) -> dict:
    ctx = ssl.create_default_context()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                raise ProviderBadResponseError(f"Invalid JSON (HTTP {status})")
            if status >= 400:
                raise _classify_error(Exception(raw), status)
            return result
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise _classify_error(Exception(body or str(e)), e.code)
    except (socket.timeout, TimeoutError):
        raise ProviderTimeoutError()
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        raise ProviderConnectionError(str(e))


def _build_openai_messages(sys_inst: str, messages: list) -> list:
    msgs = [{"role": "system", "content": sys_inst}]
    for m in messages:
        if hasattr(m, "to_openai_format"):
            msgs.append(m.to_openai_format())
        else:
            role = m.get("role", "user")
            if role in ("assistant", "model"):
                role = "assistant"
            msgs.append({"role": role, "content": m.get("content", "")})
    return msgs


# ── Google Gemini (HTTP REST) ──────────────────────────────────

def _generate_google(model_id: str, messages: list, sys_inst: str, temp: float) -> str:
    if not GOOGLE_API_KEY:
        raise ProviderAuthError("Google API key not found.")

    # Build contents for Gemini REST API
    contents = []
    for m in messages:
        role = "user" if (hasattr(m, "role") and m.role == "user") else "model"
        text = m.content if hasattr(m, "content") else ""
        contents.append({
            "role": role,
            "parts": [{"text": text}],
        })

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GOOGLE_API_KEY}"
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": sys_inst}]},
        "generationConfig": {"temperature": temp},
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ],
    }

    result = http_post(url, {"Content-Type": "application/json", **COMMON_HEADERS}, payload)
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ProviderBadResponseError("Unexpected response from Google.")


# ── Groq (HTTP REST) ───────────────────────────────────────────

def _generate_groq(model_id: str, messages: list, sys_inst: str, temp: float) -> str:
    if not GROQ_API_KEY:
        raise ProviderAuthError("Groq API key not found.")

    msgs = _build_openai_messages(sys_inst, messages)

    result = http_post(
        "https://api.groq.com/openai/v1/chat/completions",
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            **COMMON_HEADERS,
        },
        {
            "model": model_id,
            "messages": msgs,
            "temperature": temp,
        },
    )
    return result["choices"][0]["message"]["content"]


# ── OpenRouter / DeepSeek (HTTP) ───────────────────────────────

def _generate_http(provider: str, model_id: str, messages: list, sys_inst: str, temp: float) -> str:
    api_key = PROVIDER_KEYS.get(provider)
    if not api_key:
        raise ProviderAuthError(f"'{provider}' API key not found.")
    url = PROVIDER_URLS.get(provider)
    if not url:
        raise ProviderBadResponseError(f"'{provider}' URL is not defined.")

    msgs = _build_openai_messages(sys_inst, messages)

    result = http_post(
        url,
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            **COMMON_HEADERS,
        },
        {
            "model": model_id,
            "messages": msgs,
            "temperature": temp,
        },
    )
    return result["choices"][0]["message"]["content"]


# ── Unified Entry Point ────────────────────────────────────────

def generate_response(
    provider: str,
    model_id: str,
    messages: list,
    system_instruction: str,
    temperature: float = 1.4,
) -> str:
    if provider == "google":
        return _generate_google(model_id, messages, system_instruction, temperature)
    elif provider == "groq":
        return _generate_groq(model_id, messages, system_instruction, temperature)
    elif provider in ("openrouter", "deepseek"):
        return _generate_http(provider, model_id, messages, system_instruction, temperature)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ── Compatibility aliases (for external imports) ──────────────

google_client = GOOGLE_API_KEY  # truthy if key exists
groq_client = GROQ_API_KEY  # truthy if key exists
