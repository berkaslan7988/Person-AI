# Person AI 🤖

A **multi-character AI chat app** built with [Flet](https://flet.dev). Create custom AI personas, import SillyTavern character cards, and have natural conversations powered by your choice of AI model.

<img width="1848" height="968" alt="resim" src="https://github.com/user-attachments/assets/b15791d5-eca6-4475-baf9-b5517de4e73b" />

## 📱 Android

1. Download `Person AI.apk`
2. Enable **Install from unknown sources** on your device
3. Install and open the app
4. Go to **Settings → API Keys** and enter at least one API key

> API keys are stored locally on your device and never transmitted anywhere except the respective AI provider's API.

## ✨ Features

- **Multi-Character Gallery** — Create, edit, and switch between unlimited AI personas
- **SillyTavern V2 Import/Export** — Compatible with the character card ecosystem
- **AI Avatar Generation** — Generate character avatars from a text description
- **Multiple AI Providers** — Google Gemini, Groq, DeepSeek, OpenRouter
- **Streaming Responses** — Token-by-token display for a natural feel
- **Multi-Session Support** — Multiple separate chats per character
- **Session History & Search** — Browse and search across all messages
- **Theme System** — Dark/Light/System modes with accent color picker
- **TR/EN Interface** — Full bilingual support
- **SQLite Persistence** — Auto-save with session restore on startup

## 📦 Supported Models

| Model | Provider | Speed | Notes |
|-------|----------|-------|-------|
| Gemini 2.5 Flash | Google | ⚡ Fast | Free tier available |
| Llama 3.3 70B | Groq | ⚡⚡ Ultra fast | Free tier available |
| DeepSeek V3.2 | DeepSeek | 🧠 Smart | Very cheap |
| DeepSeek V4 Pro | OpenRouter | 🧠 Smart | Via OpenRouter |

You only need API keys for the providers you want to use. Getting a key:

- **Google Gemini** → [aistudio.google.com](https://aistudio.google.com) (free tier)
- **Groq** → [console.groq.com](https://console.groq.com) (free tier)
- **DeepSeek** → [platform.deepseek.com](https://platform.deepseek.com)
- **OpenRouter** → [openrouter.ai](https://openrouter.ai)

## 🖥️ Running from Source

### Prerequisites

- Python 3.10+
- Flet 0.85+

```bash
git clone https://github.com/your-username/person-ai.git
cd person-ai
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Or skip this step and enter keys in-app via **Settings → API Keys**.

### Run

```bash
flet run main.py
```

### Build APK

```bash
flet build apk
```

## 📁 Project Structure

```
Person AI/
├── main.py                  # Entry point
├── person_ai/
│   ├── app.py               # App shell, routing, splash screen
│   ├── config.py            # API keys, model list, settings
│   ├── theme.py             # Design tokens (colors, spacing, typography)
│   ├── i18n.py              # TR/EN translations
│   ├── models/
│   │   ├── character.py     # Character dataclass
│   │   └── chat_session.py  # Chat session model
│   ├── services/
│   │   ├── ai_providers.py  # Unified AI provider abstraction
│   │   ├── storage.py       # SQLite persistence layer
│   │   └── streaming.py     # Streaming response handler
│   └── ui/
│       ├── app_state.py     # Centralized app state
│       ├── components/      # Reusable UI components
│       └── screens/         # Full-page screens
├── assets/
│   └── icon.png
├── .env.example             # API key template
├── requirements.txt
└── pyproject.toml
```

## 📝 License

MIT
