"""Person AI Web — streaming chat for Gemini, Groq, OpenRouter and DeepSeek (pure urllib).

stream_chat(...) yields text chunks and raises a ProviderError subclass on failure.
Set PAI_FAKE=1 in the environment to get canned replies (for offline UI testing).
"""

import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request

from .config import OLLAMA_URL, PROVIDER_URLS, all_models, get_key

_CTX = ssl.create_default_context()
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PersonAI/3.0"
TIMEOUT = 120


class ProviderError(Exception):
    code = "unknown"

    def __init__(self, detail: str = ""):
        super().__init__(detail)
        self.detail = detail


class ProviderTimeout(ProviderError):
    code = "timeout"


class ProviderConnection(ProviderError):
    code = "connection"


class ProviderAuth(ProviderError):
    code = "auth"


class ProviderRateLimit(ProviderError):
    code = "rate_limit"


class ProviderContentFilter(ProviderError):
    code = "content_filter"


class ProviderBadResponse(ProviderError):
    code = "bad_response"


class ProviderPayment(ProviderError):
    code = "payment"


class ProviderOllamaDown(ProviderError):
    code = "ollama_down"


def _error_text(body: str) -> str:
    try:
        data = json.loads(body)
        if isinstance(data, list) and data:
            data = data[0]
        err = data.get("error", data) if isinstance(data, dict) else data
        if isinstance(err, dict):
            return str(err.get("message") or err)
        return str(err)
    except Exception:
        return body


def _classify(status: int, body: str) -> ProviderError:
    msg = _error_text(body or "")[:400]
    low = (body or "").lower()
    if status in (401, 403):
        return ProviderAuth(msg)
    if status == 402 or "insufficient balance" in low or "insufficient credits" in low:
        return ProviderPayment(msg)
    if status == 429 or "resource_exhausted" in low or "rate limit" in low or "rate_limit" in low:
        return ProviderRateLimit(msg)
    if "safety" in low or "content_filter" in low or "blocked" in low or "prohibited" in low:
        return ProviderContentFilter(msg)
    if status == 400 and ("api key" in low or "api_key" in low):
        return ProviderAuth(msg)
    return ProviderError(f"HTTP {status}: {msg}" if status else msg)


def _open(url: str, headers: dict, payload: dict, timeout: int = TIMEOUT):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": _UA, **headers},
        method="POST",
    )
    try:
        if url.startswith("http://"):
            return urllib.request.urlopen(req, timeout=timeout)
        return urllib.request.urlopen(req, context=_CTX, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        raise _classify(e.code, body or str(e.reason))
    except (socket.timeout, TimeoutError):
        raise ProviderTimeout()
    except urllib.error.URLError as e:
        if "timed out" in str(e.reason).lower():
            raise ProviderTimeout()
        raise ProviderConnection(str(e.reason))
    except OSError as e:
        raise ProviderConnection(str(e))


def _sse_data(resp, cancel):
    """Yield the payload of every `data:` line of a server-sent-events response."""
    try:
        for raw in resp:
            if cancel and cancel():
                return
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("data:"):
                yield line[5:].strip()
    except (socket.timeout, TimeoutError):
        raise ProviderTimeout()
    except OSError as e:
        raise ProviderConnection(str(e))
    finally:
        try:
            resp.close()
        except Exception:
            pass


# ── OpenAI-compatible (Groq, OpenRouter, DeepSeek) ───────────
def _stream_openai(provider, model_id, messages, system, params, cancel):
    key = get_key(provider)
    if not key:
        raise ProviderAuth(f"{provider} API key missing")
    msgs = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]
    payload = {
        "model": model_id,
        "messages": msgs,
        "temperature": params["temperature"],
        "top_p": params["top_p"],
        "max_tokens": params["max_tokens"],
        "stream": True,
    }
    # Groq rejects/ignores frequency_penalty on its models, so only send it elsewhere.
    if provider != "groq" and params["frequency_penalty"]:
        payload["frequency_penalty"] = params["frequency_penalty"]
    if "gpt-oss" in model_id:
        payload["reasoning_effort"] = "low"  # short hidden reasoning → replies start in ~0.5 s
    if provider == "openrouter" and "nemotron" in model_id:
        payload["reasoning"] = {"effort": "low", "exclude": True}  # long reasoning would eat max_tokens
    headers = {"Authorization": f"Bearer {key}", "Accept": "text/event-stream"}
    if provider == "openrouter":
        headers.update({"HTTP-Referer": "http://localhost", "X-Title": "Person AI"})

    resp = _open(PROVIDER_URLS[provider], headers, payload)
    for data in _sse_data(resp, cancel):
        if data == "[DONE]":
            return
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("error"):
            err = obj["error"]
            code = err.get("code", 0) if isinstance(err, dict) else 0
            raise _classify(code if isinstance(code, int) else 0, json.dumps(obj))
        choices = obj.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        text = delta.get("content")
        if text:
            yield text
        if choices[0].get("finish_reason") == "content_filter":
            raise ProviderContentFilter("content_filter")


# ── Google Gemini ────────────────────────────────────────────
def _stream_google(model_id, messages, system, params, cancel):
    key = get_key("google")
    if not key:
        raise ProviderAuth("google API key missing")
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        if contents and contents[-1]["role"] == role:  # merge same-role turns
            contents[-1]["parts"][0]["text"] += "\n\n" + m["content"]
        else:
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {
            "temperature": params["temperature"],
            "topP": params["top_p"],
            "maxOutputTokens": params["max_tokens"],
            # no hidden "thinking" tokens: they would eat the max-token budget
            "thinkingConfig": {"thinkingBudget": 0},
        },
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in (
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_HARASSMENT",
            )
        ],
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:streamGenerateContent?alt=sse"
    )
    resp = _open(url, {"x-goog-api-key": key}, payload)
    produced = False
    blocked = ""
    for data in _sse_data(resp, cancel):
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        if obj.get("error"):
            err = obj["error"]
            raise _classify(err.get("code", 0) if isinstance(err, dict) else 0, json.dumps(obj))
        fb = obj.get("promptFeedback") or {}
        if fb.get("blockReason"):
            blocked = fb["blockReason"]
        for cand in obj.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                if part.get("thought"):
                    continue
                text = part.get("text")
                if text:
                    produced = True
                    yield text
            if cand.get("finishReason") in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"):
                blocked = cand["finishReason"]
    if blocked and not produced:
        raise ProviderContentFilter(blocked)


# ── Ollama (local, native /api/chat — NDJSON stream) ─────────
def _stream_ollama(model_id, messages, system, params, cancel):
    options = {
        "temperature": params["temperature"],
        "top_p": params["top_p"],
        "num_predict": params["max_tokens"],
        "num_ctx": params.get("num_ctx", 8192),
    }
    if params["frequency_penalty"]:
        options["frequency_penalty"] = params["frequency_penalty"]
    payload = {
        "model": model_id,
        "messages": [{"role": "system", "content": system}]
        + [{"role": m["role"], "content": m["content"]} for m in messages],
        "stream": True,
        "options": options,
    }
    if "qwen3" in model_id.lower():
        payload["think"] = False  # hidden reasoning only adds latency in roleplay
    try:
        # the first call can be slow: the model is loaded from disk into the GPU
        resp = _open(OLLAMA_URL + "/api/chat", {}, payload, timeout=300)
    except ProviderConnection as e:
        raise ProviderOllamaDown(e.detail)
    try:
        for raw in resp:
            if cancel and cancel():
                return
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("error"):
                raise ProviderError(str(obj["error"])[:400])
            text = (obj.get("message") or {}).get("content")
            if text:
                yield text
            if obj.get("done"):
                return
    except (socket.timeout, TimeoutError):
        raise ProviderTimeout()
    except ConnectionError as e:
        raise ProviderOllamaDown(str(e))
    finally:
        try:
            resp.close()
        except Exception:
            pass


# ── Fake provider (UI testing without API calls) ─────────────
def _stream_fake(messages, cancel):
    last = messages[-1]["content"] if messages else ""
    reply = (
        f"*başını hafifçe yana eğer* \"{last[:60]}\" mi dedin? **İlginç.** "
        "Bu bir `test` yanıtıdır — gerçek model çağrılmadı.\n\n"
        "*kısa bir sessizlikten sonra gülümser* Devam edelim mi?"
    )
    for word in reply.split(" "):
        if cancel and cancel():
            return
        time.sleep(0.03)
        yield word + " "


def stream_chat(model_label: str, messages: list, system: str, params: dict, cancel=None):
    model = all_models().get(model_label)
    if not model:
        raise ProviderBadResponse(f"unknown model: {model_label}")
    provider = model["provider"]
    if os.environ.get("PAI_FAKE") == "1" and provider != "ollama":
        yield from _stream_fake(messages, cancel)
        return
    if provider == "ollama":
        yield from _stream_ollama(model["id"], messages, system, params, cancel)
    elif provider == "google":
        yield from _stream_google(model["id"], messages, system, params, cancel)
    else:
        yield from _stream_openai(provider, model["id"], messages, system, params, cancel)
