# Person AI

A self-hosted character roleplay chat app. You create characters (or import SillyTavern cards), pick a model, and
write the story together. Everything runs on your own computer: a small Python server with no dependencies, a React
interface, and a local SQLite database.

## Features

- **Characters.** Create cards with a personality, scenario, greeting, alternate greetings, example lines and tags.
  Drag and drop SillyTavern V2 cards (`.png` or `.json`) anywhere in the window to import several at once. A gallery
  with search, tag filters, sorting and favourites. Four starter characters come with every new account.
- **Chat.** Streaming replies, swipes (regenerate and flip between versions), edit and delete messages, and
  *roleplay formatting* for actions.
- **Long-term memory.** Older messages are summarised automatically once they fall out of the context window, and
  you can pin notes the character should never forget.
- **Models.** Google Gemini, Groq, DeepSeek and OpenRouter in the cloud, or local models through
  [Ollama](https://ollama.com) (no internet, no API costs). If a cloud model hits its rate limit, the app falls back to
  the next one automatically.
- **Accounts.** Username and password, no email. Each account has its own characters, chats and settings.
- **Interface.** Turkish and English, light and dark themes, custom accent colour, JSON export of all your data.
- **Optional remote access** for you and people you invite, through Cloudflare Tunnel and Cloudflare Access
  (see below).

## Requirements

- Python 3.10 or newer (standard library only, nothing to `pip install`)
- Node.js 18 or newer, only to build the interface once
- An API key for at least one cloud provider, or Ollama running locally

## Getting started

```bash
cd frontend
npm ci
npm run build        # writes the interface to ../static
cd ..
cp .env.example .env # then add your API key(s)
python server.py     # opens http://127.0.0.1:8550
```

On Windows you can double-click `baslat.bat` instead of the last step.

The first account you create also inherits any data that existed before accounts were added. API keys can be set in
`.env` or from the settings page; keys saved in the app take priority.

| Command | What it does |
| --- | --- |
| `python server.py` | Local only, on 127.0.0.1:8550 |
| `python server.py --port 9000 --no-browser` | Another port, without opening a browser |
| `baslat_yerel_ag.bat` / `python server.py --host 0.0.0.0` | Also reachable from your local network |
| `baslat_uzak.bat` | Starts the app together with a Cloudflare Tunnel (see below) |

## Where your data lives

- `data/person_ai.db`: characters, chats, accounts and settings (SQLite)
- `data/settings.json`: API keys saved from the app (obfuscated, not encrypted, so keep the folder private)
- `.env`: API keys and optional remote-access settings

None of these are tracked by git.

## Customising the roleplay rules

The system prompt starts with the character's name and description, followed by a short block of roleplay rules.
The default rules live in `DEFAULT_RULES` in `server.py`. To use your own, put them in `data/system_prompt.txt`; the
file is read on every message, so changes apply immediately. You are responsible for staying within the usage
policies of the model providers you use.

## Remote access (optional)

You can reach your own instance from your phone or let a few invited people use it, without opening any ports:

1. Add your domain to Cloudflare and install `cloudflared`.
2. In Cloudflare Zero Trust, create a self-hosted **Access application** for a hostname such as
   `chat.example.com`, with a policy that allows only the email addresses you choose.
3. Create a tunnel (`cloudflared tunnel login`, `cloudflared tunnel create person-ai`) and copy
   `deploy/cloudflared.example.yml` to `%USERPROFILE%\.cloudflared\person-ai.yml` with your values.
   Then run `cloudflared tunnel route dns person-ai chat.example.com`.
4. Set `PAI_PUBLIC_HOST`, `PAI_ACCESS_TEAM` and `PAI_ACCESS_AUD` in `.env` and start the app with `baslat_uzak.bat`.

Security model:

- The server verifies Cloudflare Access's signed token (RS256 JWT) on every tunnelled request, including static
  files, using only the standard library (`core/access.py`). Requests without a valid token get a 403. If the signing
  keys can't be fetched, the server answers 503 instead of letting requests through.
- `cloudflared` checks the same token before forwarding.
- Password resets and API-key changes are only possible from the computer running the server, never through the
  tunnel. Session cookies are marked `Secure` over the tunnel, and login rate limits use the visitor's real IP.
- With the three settings empty, remote mode is off and the app behaves as a purely local app.

## Development

```bash
cd frontend && npm run dev                 # interface with hot reload (proxies the API to :8550)
python -m unittest discover -s tests -v    # backend tests
```

Project layout:

```
server.py            HTTP server, routing, prompt building, streaming (SSE)
core/config.py       paths, providers, models, API keys
core/providers.py    Gemini, OpenAI-compatible APIs and Ollama clients
core/storage.py      SQLite storage, accounts, per-account scoping
core/access.py       Cloudflare Access JWT validation
core/starter_cards.py  the starter characters
frontend/src/        React interface
tests/               unit and integration tests
deploy/              example tunnel config
```

## License

Copyright © 2026. All rights reserved. The source is published for reference; no licence to reuse it is granted.
