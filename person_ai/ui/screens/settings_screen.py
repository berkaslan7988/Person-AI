"""Person AI - Tabbed Settings Screen.

Sections: Model · Character · Appearance · Data · Advanced
"""

import flet as ft
from ..app_state import state
from ..components.settings_section import make_section_title
from ...i18n import t
from ...theme import ACCENT_PRESETS
from ...config import (
    AVAILABLE_MODELS, MODEL_META,
    GOOGLE_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, DEEPSEEK_API_KEY,
    set_api_key, get_usable_models,
)
from ...services.storage import storage


def build_settings_screen(page: ft.Page) -> ft.Container:
    """Return the settings screen with tabbed sections."""
    c = state.theme["colors"]
    sp = state.theme["spacing"]
    rd = state.theme["radius"]
    ty = state.theme["typography"]

    # ══════════════════════════════════════════════════════════
    #  TAB BAR (within settings)
    # ══════════════════════════════════════════════════════════

    section_containers = {}  # "model" → Container, etc.
    tab_buttons = {}

    def _make_section_tab(label, key, icon):
        btn = ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=c["text_secondary"], size=16),
                ft.Text(label, color=c["text_secondary"], size=11, weight=ft.FontWeight.BOLD),
            ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=c["surface_alt"],
            border_radius=rd["btn_sm"],
            padding=ft.Padding(sp[8], sp[4], sp[8], sp[4]),
            on_click=lambda e: _switch_section(key),
        )
        tab_buttons[key] = btn
        return btn

    tabs_row = ft.Row(
        controls=[
            _make_section_tab(t("sec_model"), "model", ft.Icons.AUTO_AWESOME),
            _make_section_tab(t("sec_character"), "character", ft.Icons.PERSON),
            _make_section_tab(t("sec_appearance"), "appearance", ft.Icons.PALETTE),
            _make_section_tab(t("sec_data"), "data", ft.Icons.STORAGE),
            _make_section_tab(t("sec_advanced"), "advanced", ft.Icons.TUNE),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=sp[4],
    )

    def _mark_active_tab(key: str):
        for k, cont in section_containers.items():
            cont.visible = (k == key)
        for k, btn in tab_buttons.items():
            active = (k == key)
            btn.bgcolor = c["primary"] if active else c["surface_alt"]
            btn.content.controls[0].color = c["white"] if active else c["text_secondary"]
            btn.content.controls[1].color = c["white"] if active else c["text_secondary"]

    def _switch_section(key: str):
        state.settings_section = key  # remember across rebuilds
        _mark_active_tab(key)
        page.update()

    # ══════════════════════════════════════════════════════════
    #  1. MODEL SECTION
    # ══════════════════════════════════════════════════════════

    model_list = ft.Column(spacing=sp[8])

    def _build_model_cards():
        model_list.controls.clear()
        usable = set(state.usable_models)
        for label, data in AVAILABLE_MODELS.items():
            provider = data["provider"]
            meta = MODEL_META.get(provider, {})
            badge_key = meta.get("badge", "")
            badge = t(badge_key) if badge_key else ""
            icon_name = meta.get("icon", "AUTO_AWESOME")

            is_available = label in usable
            is_active = label == state.selected_model

            border_color = c["primary"] if is_active else c["border_subtle"]
            card = ft.Container(
                content=ft.Row([
                    ft.Icon(getattr(ft.Icons, icon_name, ft.Icons.AUTO_AWESOME),
                            color=c["primary"] if is_available else c["text_secondary"], size=22),
                    ft.Column([
                        ft.Text(label, size=13, weight=ft.FontWeight.BOLD,
                                color=c["text_primary"] if is_available else c["text_secondary"]),
                        ft.Text(badge, size=10, color=c["primary_variant"]) if badge else ft.Text(""),
                    ], spacing=2, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE if is_active else ft.Icons.RADIO_BUTTON_UNCHECKED,
                            color=c["primary"] if is_available else c["border"], size=20),
                ], spacing=sp[8]),
                bgcolor=c["surface_alt"],
                border=ft.Border(
                    ft.BorderSide(1, border_color),
                    ft.BorderSide(1, border_color),
                    ft.BorderSide(1, border_color),
                    ft.BorderSide(1, border_color),
                ),
                border_radius=rd["card"],
                padding=sp[12],
                on_click=lambda e, lbl=label: _select_model(lbl),
                ink=True,
                opacity=1.0 if is_available else 0.5,
            )
            model_list.controls.append(card)

    def _select_model(label: str):
        if label in state.usable_models:
            state.selected_model = label
            state.save_persisted_settings()
            _build_model_cards()
            if hasattr(page, "_personai_update_header"):
                page._personai_update_header()
            page.update()

    api_key_section = ft.Column(spacing=sp[8])

    def _build_api_key_fields():
        api_key_section.controls.clear()
        providers = [
            ("google", "Google Gemini", GOOGLE_API_KEY),
            ("groq", "Groq", GROQ_API_KEY),
            ("openrouter", "OpenRouter", OPENROUTER_API_KEY),
            ("deepseek", "DeepSeek", DEEPSEEK_API_KEY),
        ]
        for provider, label, current_key in providers:
            tf = ft.TextField(
                label=label,
                value=current_key,
                password=True,
                can_reveal_password=True,
                border_color=c["primary"],
                focused_border_color=c["primary_variant"],
                text_size=12,
            )
            save_btn = ft.IconButton(
                icon=ft.Icons.SAVE,
                icon_color=c["primary"],
                tooltip=f"{label} — {t('save_key_tooltip')}",
                on_click=lambda e, p=provider, f=tf: _save_key(p, f),
            )
            api_key_section.controls.append(
                ft.Row([tf, save_btn], spacing=sp[4])
            )

    def _save_key(provider: str, field: ft.TextField):
        key = field.value.strip()
        set_api_key(provider, key)
        state.usable_models = get_usable_models()
        if state.usable_models and not state.selected_model:
            state.selected_model = state.usable_models[0]
            state.save_persisted_settings()
        _build_model_cards()
        # Update chat screen header/hint if it's already built
        if hasattr(page, "_personai_update_header"):
            page._personai_update_header()
        page.show_dialog(ft.SnackBar(
            content=ft.Text(f"{provider}: {t('api_key_saved')}", color=c["white"]),
            bgcolor=c["success"],
        ))
        page.update()

    _build_model_cards()
    _build_api_key_fields()

    model_section = ft.Container(
        content=ft.Column([
            make_section_title(ft.Icons.AUTO_AWESOME, t("model_section")),
            model_list,
            ft.Divider(thickness=1, color=c["border_subtle"]),
            make_section_title(ft.Icons.KEY, t("api_keys")),
            ft.Text(t("keys_saved_info"), size=10, color=c["text_secondary"]),
            api_key_section,
        ], spacing=sp[8], scroll=ft.ScrollMode.AUTO),
        padding=sp[12],
        expand=True,
    )

    # ══════════════════════════════════════════════════════════
    #  2. CHARACTER SECTION (lightweight — full form in gallery)
    # ══════════════════════════════════════════════════════════

    char_name = ft.TextField(
        label=t("field_name"), value=state.character.name,
        border_color=c["primary"], focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
    )
    char_traits = ft.TextField(
        label=t("field_personality"), value=state.character.traits,
        multiline=True, min_lines=2, max_lines=4,
        border_color=c["primary"], focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
    )
    char_greeting = ft.TextField(
        label=t("field_greeting"), value=state.character.greeting,
        multiline=True, min_lines=2, max_lines=3,
        border_color=c["primary"], focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
    )
    char_avatar_url = ft.TextField(
        label=t("field_avatar"),
        value=state.character.avatar_url,
        hint_text=t("avatar_url_hint"),
        border_color=c["primary"], focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
        suffix=ft.Icon(ft.Icons.IMAGE, color=c["text_secondary"]),
    )

    character_section = ft.Container(
        content=ft.Column([
            make_section_title(ft.Icons.PERSON, t("character_section")),
            ft.Text(t("character_detail_hint"), size=10, color=c["text_secondary"]),
            char_name, char_traits, char_greeting, char_avatar_url,
        ], spacing=sp[8], scroll=ft.ScrollMode.AUTO),
        padding=sp[12],
        expand=True,
    )

    # ══════════════════════════════════════════════════════════
    #  3. APPEARANCE SECTION
    # ══════════════════════════════════════════════════════════

    # ── Language (applies instantly) ─────────────────────────
    language_dropdown = ft.Dropdown(
        label=t("language"),
        options=[
            ft.DropdownOption("tr", t("tr")),
            ft.DropdownOption("en", t("en")),
        ],
        value=state.language,
        border_color=c["primary"],
        focused_border_color=c["primary_variant"],
    )

    def _on_language_change(e):
        raw = getattr(e, "data", None)
        new_lang = raw if raw in ("tr", "en") else (language_dropdown.value or "tr")
        if new_lang == state.language:
            return
        language_dropdown.value = new_lang
        state.language = new_lang
        state.save_persisted_settings()
        state.settings_section = "appearance"
        if hasattr(page, "_personai_rebuild_ui"):
            page._personai_rebuild_ui(1)

    # Flet >=0.80 fires on_select; older versions fire on_change — wire both.
    language_dropdown.on_select = _on_language_change
    language_dropdown.on_change = _on_language_change

    # ── Theme mode (applies instantly) ───────────────────────
    theme_dropdown = ft.Dropdown(
        label=t("theme_mode"),
        options=[
            ft.DropdownOption("dark", t("dark")),
            ft.DropdownOption("light", t("light")),
        ],
        value=state.theme_mode if state.theme_mode in ("dark", "light") else "dark",
        border_color=c["primary"],
        focused_border_color=c["primary_variant"],
    )

    def _on_theme_change(e):
        raw = getattr(e, "data", None)
        new_mode = raw if raw in ("dark", "light") else (theme_dropdown.value or "dark")
        if new_mode == state.theme_mode:
            return
        theme_dropdown.value = new_mode
        state.theme_mode = new_mode
        state.refresh_theme()
        state.save_persisted_settings()
        state.settings_section = "appearance"
        if hasattr(page, "_personai_rebuild_ui"):
            page._personai_rebuild_ui(1)

    theme_dropdown.on_select = _on_theme_change
    theme_dropdown.on_change = _on_theme_change

    # ── Accent color swatches (applies instantly) ────────────
    def _on_accent_pick(e):
        new_accent = e.control.data or ""
        if new_accent == state.accent_color:
            return
        state.accent_color = new_accent
        state.refresh_theme()
        state.save_persisted_settings()
        state.settings_section = "appearance"
        if hasattr(page, "_personai_rebuild_ui"):
            page._personai_rebuild_ui(1)

    def _accent_swatch(hex_color: str) -> ft.Container:
        is_default = hex_color == ""
        is_active = (state.accent_color or "") == hex_color
        fill = hex_color if hex_color else c["primary"]
        return ft.Container(
            width=34, height=34, border_radius=17,
            bgcolor=fill,
            data=hex_color,
            on_click=_on_accent_pick,
            ink=True,
            alignment=ft.Alignment(0, 0),
            tooltip=t("accent_default") if is_default else hex_color,
            border=ft.Border(
                ft.BorderSide(3 if is_active else 1, c["text_primary"] if is_active else c["border"]),
                ft.BorderSide(3 if is_active else 1, c["text_primary"] if is_active else c["border"]),
                ft.BorderSide(3 if is_active else 1, c["text_primary"] if is_active else c["border"]),
                ft.BorderSide(3 if is_active else 1, c["text_primary"] if is_active else c["border"]),
            ),
            content=(ft.Icon(ft.Icons.FORMAT_COLOR_RESET, size=16, color=c["white"])
                     if is_default else
                     (ft.Icon(ft.Icons.CHECK, size=16, color=c["white"]) if is_active else None)),
        )

    accent_row = ft.Row(
        [_accent_swatch(hex_color) for hex_color, _name in ACCENT_PRESETS],
        spacing=sp[8],
        wrap=True,
    )

    # ── Chat background URL ──────────────────────────────────
    chat_bg_field = ft.TextField(
        label=t("chat_bg_label"),
        value=state.chat_background_url,
        hint_text=t("chat_bg_hint"),
        border_color=c["primary"],
        focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
        suffix=ft.Icon(ft.Icons.WALLPAPER, color=c["text_secondary"]),
    )

    # ── User profile ─────────────────────────────────────────
    user_name_field = ft.TextField(
        label=t("user_name_label"),
        value=state.user_name,
        hint_text=t("user_name_hint"),
        border_color=c["primary"],
        focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
        suffix=ft.Icon(ft.Icons.PERSON_OUTLINE, color=c["text_secondary"]),
    )

    user_avatar_field = ft.TextField(
        label=t("user_avatar_label"),
        value=state.user_avatar_url,
        hint_text=t("user_avatar_hint"),
        border_color=c["primary"],
        focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
        suffix=ft.Icon(ft.Icons.FACE, color=c["text_secondary"]),
    )

    user_persona_field = ft.TextField(
        label=t("user_persona_label"),
        value=state.user_persona,
        hint_text=t("user_persona_hint"),
        multiline=True, min_lines=3, max_lines=6,
        border_color=c["primary"],
        focused_border_color=c["primary_variant"],
        text_size=ty["body"][0],
    )

    appearance_section = ft.Container(
        content=ft.Column([
            make_section_title(ft.Icons.TRANSLATE, t("language")),
            language_dropdown,
            ft.Divider(thickness=1, color=c["border_subtle"]),
            make_section_title(ft.Icons.PALETTE, t("theme")),
            theme_dropdown,
            ft.Text(t("accent"), size=12, color=c["text_secondary"]),
            accent_row,
            ft.Divider(thickness=1, color=c["border_subtle"]),
            make_section_title(ft.Icons.WALLPAPER, t("chat_bg_section")),
            ft.Text(t("chat_bg_desc"), size=10, color=c["text_secondary"]),
            chat_bg_field,
            ft.Divider(thickness=1, color=c["border_subtle"]),
            make_section_title(ft.Icons.MANAGE_ACCOUNTS, t("user_profile_section")),
            ft.Text(t("user_profile_desc"), size=10, color=c["text_secondary"]),
            user_name_field,
            user_avatar_field,
            ft.Text(t("user_persona_desc"), size=10, color=c["text_secondary"]),
            user_persona_field,
        ], spacing=sp[8], scroll=ft.ScrollMode.AUTO),
        padding=sp[12],
        expand=True,
    )

    # ══════════════════════════════════════════════════════════
    #  4. DATA SECTION
    # ══════════════════════════════════════════════════════════

    def _delete_character_data(char_id, char_name_):
        def confirm(e):
            storage.delete_character(char_id)
            page.pop_dialog()
            _build_data_section()
            page.show_dialog(ft.SnackBar(
                content=ft.Text(f"'{char_name_}' {t('char_deleted')}", color=c["white"]),
                bgcolor=c["error"],
            ))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"'{char_name_}' {t('delete_confirm_title')}"),
            content=ft.Text(t("delete_confirm_body")),
            actions=[
                ft.TextButton(t("btn_cancel"), on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(t("btn_delete"), on_click=confirm, bgcolor=c["error"], color=c["white"]),
            ],
            bgcolor=c["surface_alt"],
        )
        page.show_dialog(dialog)

    def _reset_all(e):
        def confirm(e2):
            storage.reset_all()
            state.session.clear()
            state.session.id = None
            state.session.character_id = None
            # Keep current settings alive after a data reset
            state.save_persisted_settings()
            page.pop_dialog()
            _build_data_section()
            if hasattr(page, "_personai_render_chat"):
                page._personai_render_chat(False)
            page.show_dialog(ft.SnackBar(
                content=ft.Text(t("all_reset_done"), color=c["white"]),
                bgcolor=c["error"],
            ))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("reset_confirm_title")),
            content=ft.Text(t("reset_confirm_body")),
            actions=[
                ft.TextButton(t("btn_cancel"), on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(t("reset_btn"), on_click=confirm, bgcolor=c["error"], color=c["white"]),
            ],
            bgcolor=c["surface_alt"],
        )
        page.show_dialog(dialog)

    data_list = ft.Column(spacing=sp[8])

    def _build_data_section():
        data_list.controls.clear()
        chars = storage.list_characters()
        for char in chars:
            sessions = storage.list_sessions(char.id)
            data_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PERSON, color=c["primary"], size=18),
                        ft.Column([
                            ft.Text(char.name, size=13, weight=ft.FontWeight.BOLD, color=c["text_primary"]),
                            ft.Text(f"{len(sessions)} {t('sessions_count')}", size=10, color=c["text_secondary"]),
                        ], expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE, icon_color=c["error"], icon_size=18,
                            tooltip=t("btn_delete"),
                            on_click=lambda e, cid=char.id, cn=char.name: _delete_character_data(cid, cn),
                        ),
                    ], spacing=sp[8]),
                    bgcolor=c["surface_alt"],
                    border_radius=rd["card"],
                    padding=sp[8],
                )
            )
        if not chars:
            data_list.controls.append(ft.Text(t("no_data"), size=12, color=c["text_secondary"]))
        page.update()

    _build_data_section()

    data_section = ft.Container(
        content=ft.Column([
            make_section_title(ft.Icons.STORAGE, t("data_section")),
            ft.Text(t("saved_characters"), size=13, weight=ft.FontWeight.BOLD, color=c["text_primary"]),
            data_list,
            ft.Divider(thickness=1, color=c["border_subtle"]),
            ft.ElevatedButton(
                t("reset_all"),
                on_click=_reset_all,
                icon=ft.Icons.WARNING,
                color=c["white"], bgcolor=c["error"],
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=rd["btn_sm"])),
            ),
        ], spacing=sp[8], scroll=ft.ScrollMode.AUTO),
        padding=sp[12],
        expand=True,
    )

    # ══════════════════════════════════════════════════════════
    #  5. ADVANCED SECTION
    # ══════════════════════════════════════════════════════════

    # temperature
    temp_slider = ft.Slider(
        min=0.0, max=2.0, divisions=20, value=state.temperature, label="{value}",
        active_color=c["primary"], inactive_color=c["border"],
    )
    temp_text = ft.Text(f"{state.temperature:.1f}", weight=ft.FontWeight.BOLD, color=c["primary_variant"], size=ty["label"][0])

    # top_p
    top_p_slider = ft.Slider(
        min=0.0, max=1.0, divisions=20, value=state.top_p, label="{value:.2f}",
        active_color=c["primary"], inactive_color=c["border"],
    )
    top_p_text = ft.Text(f"{state.top_p:.2f}", weight=ft.FontWeight.BOLD, color=c["primary_variant"], size=ty["label"][0])

    # frequency_penalty
    fp_slider = ft.Slider(
        min=-2.0, max=2.0, divisions=40, value=state.frequency_penalty, label="{value:.1f}",
        active_color=c["primary"], inactive_color=c["border"],
    )
    fp_text = ft.Text(f"{state.frequency_penalty:.1f}", weight=ft.FontWeight.BOLD, color=c["primary_variant"], size=ty["label"][0])

    # max_tokens
    tokens_slider = ft.Slider(
        min=256, max=8192, divisions=31, value=state.max_tokens, label="{value}",
        active_color=c["primary"], inactive_color=c["border"],
    )
    tokens_text = ft.Text(f"{state.max_tokens}", weight=ft.FontWeight.BOLD, color=c["primary_variant"], size=ty["label"][0])

    # memory
    mem_slider = ft.Slider(
        min=4, max=50, divisions=46, value=state.memory_size, label="{value}",
        active_color=c["primary"], inactive_color=c["border"],
    )
    mem_text = ft.Text(f"{state.memory_size}", weight=ft.FontWeight.BOLD, color=c["primary_variant"], size=ty["label"][0])

    temp_slider.on_change = lambda e: (setattr(temp_text, "value", f"{e.control.value:.1f}"), page.update())
    top_p_slider.on_change = lambda e: (setattr(top_p_text, "value", f"{e.control.value:.2f}"), page.update())
    fp_slider.on_change = lambda e: (setattr(fp_text, "value", f"{e.control.value:.1f}"), page.update())
    tokens_slider.on_change = lambda e: (setattr(tokens_text, "value", f"{int(e.control.value)}"), page.update())
    mem_slider.on_change = lambda e: (setattr(mem_text, "value", f"{int(e.control.value)}"), page.update())

    advanced_section = ft.Container(
        content=ft.Column([
            make_section_title(ft.Icons.TUNE, t("advanced_section")),

            ft.Row([ft.Text(t("temperature_label"), size=12, color=c["text_secondary"]), temp_text],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            temp_slider,

            ft.Row([ft.Text(t("top_p_label"), size=12, color=c["text_secondary"]), top_p_text],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            top_p_slider,

            ft.Row([ft.Text(t("fp_label"), size=12, color=c["text_secondary"]), fp_text],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            fp_slider,

            ft.Row([ft.Text(t("max_tokens_label"), size=12, color=c["text_secondary"]), tokens_text],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            tokens_slider,

            ft.Divider(thickness=1, color=c["border_subtle"]),

            ft.Row([ft.Text(t("context_label"), size=12, color=c["text_secondary"]), mem_text],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            mem_slider,
        ], spacing=sp[4], scroll=ft.ScrollMode.AUTO),
        padding=sp[12],
        expand=True,
    )

    # ══════════════════════════════════════════════════════════
    #  APPLY BUTTON
    # ══════════════════════════════════════════════════════════

    def apply_all(e):
        # Character
        state.character.name = char_name.value
        state.character.traits = char_traits.value
        state.character.greeting = char_greeting.value
        state.character.avatar_url = char_avatar_url.value.strip()
        state.avatar_url = state.character.avatar_url
        state.session.character_name = char_name.value

        # Persist character changes (quick edits here weren't saved to DB before)
        try:
            new_id = storage.save_character(state.character)
            state.character.id = new_id
            state.session.character_id = new_id
        except Exception:
            pass

        # Advanced
        state.temperature = temp_slider.value
        state.top_p = top_p_slider.value
        state.frequency_penalty = fp_slider.value
        state.max_tokens = int(tokens_slider.value)
        state.memory_size = int(mem_slider.value)

        # Display / personalization
        state.chat_background_url = chat_bg_field.value.strip()
        state.user_name = user_name_field.value.strip()
        state.user_avatar_url = user_avatar_field.value.strip()
        state.user_persona = user_persona_field.value.strip()

        # Persist everything (language/theme are already saved on change)
        state.save_persisted_settings()

        if hasattr(page, "_personai_show_chat"):
            page._personai_show_chat()

        page.show_dialog(ft.SnackBar(
            content=ft.Text(t("settings_applied"), color=c["white"]),
            bgcolor=c["success"],
        ))
        page.update()

    apply_btn = ft.ElevatedButton(
        t("apply_all"),
        on_click=apply_all,
        color=c["white"], bgcolor=c["primary"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=rd["input"])),
    )

    # ══════════════════════════════════════════════════════════
    #  REGISTER SECTION CONTAINERS
    # ══════════════════════════════════════════════════════════

    for key, container in [
        ("model", model_section),
        ("character", character_section),
        ("appearance", appearance_section),
        ("data", data_section),
        ("advanced", advanced_section),
    ]:
        section_containers[key] = container

    # Restore the last active section (survives language/theme rebuilds)
    initial_section = state.settings_section if state.settings_section in section_containers else "model"
    _mark_active_tab(initial_section)

    section_stack = ft.Stack(
        controls=list(section_containers.values()),
        expand=True,
    )

    # ══════════════════════════════════════════════════════════
    #  BUILD
    # ══════════════════════════════════════════════════════════

    return ft.Container(
        bgcolor=c["bg"],
        padding=ft.Padding(sp[8], sp[8], sp[8], sp[4]),
        content=ft.Column(
            controls=[
                ft.Container(
                    content=tabs_row,
                    padding=ft.Padding(0, 0, 0, sp[8]),
                ),
                section_stack,
                ft.Container(
                    content=apply_btn,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(0, sp[8], 0, sp[4]),
                ),
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )
