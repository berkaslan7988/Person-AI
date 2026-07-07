"""Person AI - Streaming response support (pure HTTP, no SDKs).

Supports: Groq, OpenRouter, DeepSeek — all via HTTP SSE.
Google Gemini streaming via HTTP is also supported.
Called via asyncio.to_thread to keep the Flet UI responsive.
"""

import json
import ssl
import urllib.request
import urllib.error
from typing import Generator, Optional

from ..config import PROVIDER_KEYS, PROVIDER_URLS, GOOGLE_API_KEY, GROQ_API_KEY

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "Accept": "application/json",
}


class StreamCancelled(Exception):
    pass

STREAM_PROVIDERS = {"google", "groq", "openrouter", "deepseek"}

def _build_messages(system_instruction: str, messages: list) -> list:
    msgs = [{"role": "system", "content": system_instruction}]
    for m in messages:
        if hasattr(m, "to_openai_format"):
            msgs.append(m.to_openai_format())
        else:
            role = m.get("role", "user")
            if role in ("assistant", "model"):
                role = "assistant"
            msgs.append({"role": role, "content": m.get("content", "")})
    return msgs

def _stream_http_sse(url, headers, payload, timeout=120, cancel_flag=None):
    ctx = ssl.create_default_context()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            for raw_line in resp:
                if cancel_flag and cancel_flag():
                    raise StreamCancelled()
                line = raw_line.decode("utf-8").strip()
                if not line: continue
                if line.startswith("data: "):
                    ds = line[6:]
                    if ds == "[DONE]": break
                    try:
                        data = json.loads(ds)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content: yield content
                    except (json.JSONDecodeError, KeyError, IndexError): continue
    except StreamCancelled: raise
    except urllib.error.HTTPError as e:
        try: body = e.read().decode("utf-8")[:400]
        except Exception: body = ""
        raise RuntimeError(f"Stream error: HTTP {e.code} — {body or e.reason}")
    except Exception as e: raise RuntimeError(f"Stream error: {str(e)}")

def _stream_groq(model_id, messages, sys_inst, temp, cancel_flag):
    if not GROQ_API_KEY: raise RuntimeError("Groq API key not set.")
    msgs = _build_messages(sys_inst, messages)
    yield from _stream_http_sse(
        "https://api.groq.com/openai/v1/chat/completions",
        {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}", **COMMON_HEADERS},
        {"model": model_id, "messages": msgs, "temperature": temp, "stream": True},
        cancel_flag=cancel_flag)

def _stream_openai_compat(provider, model_id, messages, sys_inst, temp, cancel_flag):
    api_key = PROVIDER_KEYS.get(provider)
    if not api_key: raise RuntimeError(f"Provider '{provider}' API key not set.")
    url = PROVIDER_URLS.get(provider)
    if not url: raise RuntimeError(f"Provider '{provider}' has no configured URL.")
    msgs = _build_messages(sys_inst, messages)
    yield from _stream_http_sse(
        url,
        {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}", **COMMON_HEADERS},
        {"model": model_id, "messages": msgs, "temperature": temp, "stream": True},
        cancel_flag=cancel_flag)

def _stream_google(model_id, messages, sys_inst, temp, cancel_flag):
    if not GOOGLE_API_KEY: raise RuntimeError("Google API key not set.")
    contents = []
    for m in messages:
        role = "user" if (hasattr(m, "role") and m.role == "user") else "model"
        text = m.content if hasattr(m, "content") else ""
        contents.append({"role": role, "parts": [{"text": text}]})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={GOOGLE_API_KEY}"
    payload = {"contents": contents, "systemInstruction": {"parts": [{"text": sys_inst}]}, "generationConfig": {"temperature": temp}}
    ctx = ssl._create_unverified_context()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **COMMON_HEADERS}, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            for raw_line in resp:
                if cancel_flag and cancel_flag(): raise StreamCancelled()
                line = raw_line.decode("utf-8").strip()
                if not line: continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        candidates = data.get("candidates", [])
                        if candidates:
                            for part in candidates[0].get("content", {}).get("parts", []):
                                if "text" in part: yield part["text"]
                    except (json.JSONDecodeError, KeyError, IndexError): continue
    except StreamCancelled: raise
    except urllib.error.HTTPError as e:
        try: body = e.read().decode("utf-8")[:400]
        except Exception: body = ""
        raise RuntimeError(f"Google stream error: HTTP {e.code} — {body or e.reason}")
    except Exception as e: raise RuntimeError(f"Google stream error: {str(e)}")

def stream_response(provider, model_id, messages, system_instruction, temperature=1.4, cancel_flag=None):
    if provider not in STREAM_PROVIDERS: raise ValueError(f"Provider '{provider}' does not support streaming.")
    if provider == "groq": yield from _stream_groq(model_id, messages, system_instruction, temperature, cancel_flag)
    elif provider in ("openrouter", "deepseek"): yield from _stream_openai_compat(provider, model_id, messages, system_instruction, temperature, cancel_flag)
    elif provider == "google": yield from _stream_google(model_id, messages, system_instruction, temperature, cancel_flag)