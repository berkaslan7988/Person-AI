"""Character detail dialog — two tabs: Edit and Session History."""
import flet as ft
from ..app_state import state
from ...models.character import Character
from ...models.chat_session import ChatSession, Message
from ...services.storage import storage
from ...i18n import t


def build_character_detail(
    page: ft.Page,
    character: Character,
    on_saved: callable = None,
    on_chat_started: callable = None,
) -> ft.AlertDialog:
    """Return a two-tab AlertDialog: Edit | Chats."""
    tc = state.theme["colors"]
    sp = state.theme["spacing"]
    rd = state.theme["radius"]
    ty = state.theme["typography"]

    # ── Tab 1: Edit ───────────────────────────────────────────
    # We embed a lightweight inline form (not the form dialog) as a tab.
    name_field = ft.TextField(
        label=t("field_name"), value=character.name,
        border_color=tc["primary"], focused_border_color=tc["primary_variant"],
        text_size=ty["body"][0],
    )
    traits_field = ft.TextField(
        label=t("field_traits"), value=character.traits,
        multiline=True, min_lines=3, max_lines=6,
        border_color=tc["primary"], focused_border_color=tc["primary_variant"],
        text_size=ty["body"][0],
    )
    greeting_field = ft.TextField(
        label=t("field_greeting"), value=character.greeting,
        multiline=True, min_lines=2, max_lines=4,
        border_color=tc["primary"], focused_border_color=tc["primary_variant"],
        text_size=ty["body"][0],
    )
    avatar_field = ft.TextField(
        label=t("field_avatar"), value=character.avatar_url or "",
        border_color=tc["primary"], focused_border_color=tc["primary_variant"],
        text_size=ty["body"][0],
    )
    tags_field = ft.TextField(
        label=t("tags_label"), value=", ".join(character.tags or []),
        border_color=tc["primary"], focused_border_color=tc["primary_variant"],
        text_size=ty["body"][0],
        hint_text=t("tags_hint"),
    )

    def save_character(e):
        character.name = name_field.value.strip() or character.name
        character.traits = traits_field.value.strip()
        character.greeting = greeting_field.value.strip()
        character.avatar_url = avatar_field.value.strip()
        character.tags = [tag.strip() for tag in tags_field.value.split(",") if tag.strip()]
        storage.save_character(character)
        if state.character and state.character.id == character.id:
            state.character = character
            state.avatar_url = character.avatar_url
            if hasattr(page, "_personai_update_header"):
                page._personai_update_header()
        page.pop_dialog()
        if on_saved:
            on_saved(character)
        page.show_dialog(ft.SnackBar(
            content=ft.Text(f"'{character.name}' {t('char_saved')}", color=tc["white"]),
            bgcolor=tc["success"],
        ))

    edit_tab_content = ft.Column(
        [
            name_field, traits_field, greeting_field,
            avatar_field, tags_field,
            ft.Container(
                content=ft.ElevatedButton(
                    t("btn_save"), on_click=save_character,
                    bgcolor=tc["primary"], color=tc["white"],
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=rd["btn_sm"])),
                    expand=True,
                ),
                padding=ft.Padding(0, sp[8], 0, 0),
            ),
        ],
        spacing=sp[8],
        scroll=ft.ScrollMode.AUTO,
        height=420,
    )

    # ── Tab 2: Session history ────────────────────────────────
    sessions_list = ft.ListView(spacing=4, expand=True)

    def _load_sessions():
        sessions_list.controls.clear()
        sessions = storage.list_sessions(character.id)
        if not sessions:
            sessions_list.controls.append(ft.Container(
                content=ft.Text(
                    t("no_sessions"),
                    color=tc["text_secondary"], size=ty["body"][0],
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.Alignment(0, 0),
                padding=ft.Padding(0, sp[32], 0, 0),
            ))
            return

        for s in sessions:
            session = s
            msg_count = len(s.messages)
            preview = ""
            for m in reversed(s.messages):
                if m.role == "assistant":
                    preview = m.content[:80] + ("..." if len(m.content) > 80 else "")
                    break
            title = s.title or s.character_name or t("new_chat")
            updated = (s.updated_at or "")[:16].replace("T", " ")

            def _continue(e, sess=session):
                state.character = character
                state.avatar_url = character.avatar_url
                state.session = sess
                page.pop_dialog()
                if hasattr(page, "_personai_show_chat"):
                    page._personai_show_chat()
                if hasattr(page, "_personai_update_header"):
                    page._personai_update_header()
                if hasattr(page, "_personai_render_chat"):
                    page._personai_render_chat()
                if on_chat_started:
                    on_chat_started(sess)

            def _delete_session(e, sess=session):
                def confirm(e2):
                    storage.delete_session(sess.id)
                    page.pop_dialog()  # close the confirm dialog
                    _load_sessions()   # refresh the list in place
                    try:
                        sessions_list.update()
                    except Exception:
                        page.update()

                page.show_dialog(ft.AlertDialog(
                    modal=True,
                    title=ft.Text(t("delete_session_title")),
                    content=ft.Text(t("irreversible")),
                    actions=[
                        ft.TextButton(t("btn_cancel"), on_click=lambda e: page.pop_dialog()),
                        ft.ElevatedButton(t("btn_delete"), on_click=confirm,
                                          bgcolor=tc["error"], color=tc["white"]),
                    ],
                    bgcolor=tc["surface_alt"],
                ))

            card = ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row([
                                    ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                                            color=tc["text_primary"], expand=True),
                                    ft.Text(f"{msg_count} {t('messages_count')}", size=11,
                                            color=tc["text_secondary"]),
                                ]),
                                ft.Text(preview, size=12, color=tc["text_secondary"],
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(updated, size=11, color=tc["primary_variant"]),
                            ],
                            spacing=3, expand=True,
                        ),
                        ft.Column(
                            [
                                ft.Container(
                                    content=ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE,
                                                    size=22, color=tc["primary"]),
                                    on_click=_continue,
                                    ink=True,
                                    padding=ft.Padding(4, 4, 4, 4),
                                    border_radius=ft.BorderRadius(20, 20, 20, 20),
                                    tooltip=t("continue_chat"),
                                    data=session.id,
                                ),
                                ft.Container(
                                    content=ft.Icon(ft.Icons.DELETE_OUTLINE,
                                                    size=20, color=tc["error"]),
                                    on_click=_delete_session,
                                    ink=True,
                                    padding=ft.Padding(4, 4, 4, 4),
                                    border_radius=ft.BorderRadius(20, 20, 20, 20),
                                    tooltip=t("tooltip_delete"),
                                    data=session.id,
                                ),
                            ],
                            spacing=4,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    spacing=sp[8],
                ),
                bgcolor=tc["surface"],
                border_radius=ft.BorderRadius(rd["card"], rd["card"], rd["card"], rd["card"]),
                padding=ft.Padding(sp[12], sp[8], sp[8], sp[8]),
                margin=ft.Margin(0, 0, 0, 4),
            )
            sessions_list.controls.append(card)

    _load_sessions()

    history_tab_content = ft.Container(
        content=sessions_list,
        height=420,
    )

    # ── New chat button ───────────────────────────────────────
    def _new_chat(e):
        state.character = character
        state.avatar_url = character.avatar_url
        state.session = ChatSession(
            character_id=character.id,
            character_name=character.name,
        )
        if character.greeting:
            state.session.messages = [Message(role="assistant", content=character.greeting)]
        page.pop_dialog()
        if hasattr(page, "_personai_show_chat"):
            page._personai_show_chat()
        if hasattr(page, "_personai_update_header"):
            page._personai_update_header()
        if hasattr(page, "_personai_render_chat"):
            page._personai_render_chat()
        if on_chat_started:
            on_chat_started(None)
        page.show_dialog(ft.SnackBar(
            content=ft.Text(f"'{character.name}' {t('new_chat_with')}", color=tc["white"]),
            bgcolor=tc["success"],
        ))

    # ── Custom Tabs (ft.Tab API'si versiyonlar arası uyumsuz, manuel yapıyoruz) ──
    _selected_tab = [0]  # mutable ref

    tab_body = ft.Container(
        content=ft.Container(content=edit_tab_content, padding=ft.Padding(0, sp[12], 0, 0)),
        expand=True,
    )

    def _make_tab_btn(label, icon, index):
        is_active = _selected_tab[0] == index
        return ft.Container(
            content=ft.Row(
                [ft.Icon(icon, size=15, color=tc["primary"] if is_active else tc["text_secondary"]),
                 ft.Text(label, size=13, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL,
                         color=tc["primary"] if is_active else tc["text_secondary"])],
                tight=True, spacing=4,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            border=ft.Border(
                bottom=ft.BorderSide(2, tc["primary"]) if is_active else ft.BorderSide(2, ft.Colors.TRANSPARENT)
            ),
            on_click=lambda e, i=index: _switch_tab(i),
            ink=True,
        )

    tab_bar_row = ft.Row(spacing=0)

    def _rebuild_tab_bar():
        tab_bar_row.controls = [
            _make_tab_btn(t("tab_edit"),     ft.Icons.EDIT_OUTLINED, 0),
            _make_tab_btn(t("tab_sessions"), ft.Icons.HISTORY,       1),
        ]

    def _switch_tab(index):
        _selected_tab[0] = index
        _rebuild_tab_bar()
        if index == 0:
            tab_body.content = ft.Container(content=edit_tab_content,    padding=ft.Padding(0, sp[12], 0, 0))
        else:
            tab_body.content = ft.Container(content=history_tab_content, padding=ft.Padding(0, sp[12], 0, 0))
        tab_bar_row.update()
        tab_body.update()

    _rebuild_tab_bar()

    tab_divider = ft.Divider(height=1, color=tc.get("border", tc["text_secondary"]))

    tabs = ft.Column(
        [
            tab_bar_row,
            tab_divider,
            tab_body,
        ],
        spacing=0,
        expand=True,
    )

    # ── Header with avatar + name + new-chat button ───────────
    av_url = character.avatar_url
    avatar_widget = (
        ft.Container(
            content=ft.Image(src=av_url, fit=ft.BoxFit.COVER, width=36, height=36),
            width=36, height=36, border_radius=18,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ) if av_url else
        ft.Container(
            content=ft.Icon(ft.Icons.SMART_TOY, size=20, color=tc.get("bubble_text_ai", tc["white"])),
            width=36, height=36, border_radius=18,
            bgcolor=tc["ai_bubble"], alignment=ft.Alignment(0, 0),
        )
    )

    dialog_title = ft.Row(
        [
            avatar_widget,
            ft.Text(character.name, size=16, weight=ft.FontWeight.BOLD,
                    color=tc["text_primary"], expand=True),
            ft.ElevatedButton(
                t("btn_new_chat"), on_click=_new_chat,
                bgcolor=tc["primary"], color=tc["white"],
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=rd["btn_sm"]),
                    padding=ft.Padding(10, 6, 10, 6),
                ),
            ),
        ],
        spacing=sp[8],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    return ft.AlertDialog(
        modal=True,
        title=dialog_title,
        content=ft.Container(
            content=tabs,
            width=480,
            height=520,
        ),
        actions=[
            ft.TextButton(t("btn_close"), on_click=lambda e: page.pop_dialog()),
        ],
        bgcolor=tc["surface_alt"],
        content_padding=ft.Padding(sp[16], sp[8], sp[16], sp[8]),
    )
