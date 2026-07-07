# Changelog

## [2.1.0] — 2026-07-07

### Added
- **Persistent Settings** — language, theme mode, accent color, selected model and all model parameters now survive app restarts
- **Theme Mode Selector** — Dark/Light toggle in Settings → Appearance, applied instantly
- **Accent Color Picker** — preset color swatches, applied instantly across the whole UI
- **Instant Language Switching** — choosing TR/EN rebuilds the entire UI in place, no restart needed

### Fixed
- Message timestamps are now preserved when chats are saved and reloaded
- Corrupt session/character rows in the database no longer break history lists
- Deleting a session inside the character detail dialog now refreshes the list correctly
- Legible bubble and icon colors in the light theme

### Changed
- All UI strings routed through the TR/EN i18n layer (hardcoded Turkish texts removed)
- Provider error messages and model badges are now localized (TR/EN)

## [2.0.0] — 2026-06-21

### Added
- **Multi-Character System** — character gallery with card grid, create/edit/delete, SillyTavern V2 import/export
- **AI Avatar Generation** — Pollinations.ai integration for generating character avatars from description
- **Streaming Responses** — Groq, OpenRouter, DeepSeek streaming support with token-by-token display
- **DeepSeek Provider** — V3.2 model with OpenAI-compatible API integration
- **Multi-Session Support** — Same character, multiple separate chat sessions
- **Session History & Search** — BottomSheet overlay with search/filter across all messages
- **Tabbed Settings** — Model · Character · Appearance · Data · Advanced sections
- **Advanced Parameters** — top_p, frequency_penalty, max_tokens sliders
- **API Key Management** — In-app key entry with local base64 obfuscation storage
- **Theme System** — Dark/Light/System modes + accent color picker
- **TR/EN Internationalization** — Bilingual interface with language toggle
- **Splash Screen + Onboarding** — First-launch 3-step wizard
- **Skeleton Loading** — Shimmer placeholders during initialization
- **Animated Tab Transitions** — Fade animation between tabs
- **Message Context Menu** — Long-press for Copy/Delete/Edit/Regenerate
- **Swipe-to-Regenerate** — Swipe AI message right to regenerate
- **Markdown RP Formatting** — *italic*, **bold**, `code` rendering
- **Typing Indicator** — Animated 3-dot pulse animation
- **Scroll-to-Bottom Button** — Auto-appearing floating button
- **Empty State** — Character intro card with greeting when chat is empty
- **Header Bar** — Character avatar + name + model badge
- **Persistence** — SQLite with auto-save, last session restore on startup

### Changed
- Complete architectural refactor: single-file to modular package (`person_ai/`)
- Moved from closure variables to centralized `AppState` dataclass
- All API calls now async with `asyncio.to_thread`
- Theme tokens centralized in `theme.py` (colors, spacing, typography, radius)
- API keys moved to `.env` + `python-dotenv`

### Fixed
- UI freeze during sync API calls → async architecture
- Hard-coded values → design tokens
- Error handling → typed `ProviderError` subclasses with user-friendly messages

## [1.0.0] — Initial Release
- Basic single-character chat with Google Gemini, Groq, OpenRouter
- Dark theme UI with Flet
- Character settings: name, traits, avatar URL
- Temperature and memory sliders
- Chat export to file