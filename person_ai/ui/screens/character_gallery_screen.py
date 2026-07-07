"""Person AI - Character gallery screen (multi-character system).

Features:
- Card grid with avatar, name, summary, last session line, new chat button
- Create / Edit / Delete characters via AlertDialog form
- SillyTavern V2 import/export
"""

import json
import os
import flet as ft
from ..app_state import state
from ..components.character_card import character_card
from ...models.character import Character
from ...models.chat_session import ChatSession
from ...services.storage import storage
from ...i18n import t


def build_character_gallery_screen(page: ft.Page) -> ft.Container:
    """Return the character gallery screen with card grid + toolbar."""
    th = state.theme
    c = th["colors"]
    sp = th["spacing"]
    rd = th["radius"]
    ty = th["typography"]

    def _get_last_session_text(character_id: int) -> str:
        sessions = storage.list_sessions(character_id)
        if sessions:
            last = sessions[0]
            msgs = last.messages
            if msgs:
                preview = msgs[-1].content[:50]
                return preview + "..." if len(msgs[-1].content) > 50 else preview
            return t("empty_chat")
        return ""

    grid = ft.GridView(
        expand=True,
        max_extent=200,
        child_aspect_ratio=0.75,
        spacing=sp[8],
        run_spacing=sp[8],
        padding=ft.Padding(sp[12], sp[12], sp[12], sp[12]),
    )

    def refresh_grid():
        grid.controls.clear()
        characters = storage.list_characters()
        for char in characters:
            session_summary = _get_last_session_text(char.id)
            grid.controls.append(
                character_card(
                    character=char,
                    last_session_summary=session_summary,
                    on_tap=lambda e, ch=char: _open_character_detail(ch),
                    on_new_chat=lambda e, ch=char: _start_new_chat(ch),
                )
            )
        if not characters:
            grid.controls.append(
                ft.Container(
                    content=ft.Text(
                        t("no_characters"),
                        size=ty["body"][0],
                        color=c["text_secondary"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=sp[32],
                )
            )
        page.update()

    def _start_new_chat(char: Character):
        state.character = char
        state.avatar_url = char.avatar_url
        state.session = ChatSession(
            character_id=char.id,
            character_name=char.name,
        )
        if char.greeting:
            from ...models.chat_session import Message
            state.session.messages = [Message(role="assistant", content=char.greeting)]

        if hasattr(page, "_personai_show_chat"):
            page._personai_show_chat()
        if hasattr(page, "_personai_update_header"):
            page._personai_update_header()
        if hasattr(page, "_personai_render_chat"):
            page._personai_render_chat()
        page.show_dialog(ft.SnackBar(
            content=ft.Text(f"'{char.name}' {t('chat_started')}", color=c["white"]),
            bgcolor=c["success"],
        ))

    def _open_create_form(e=None):
        from .character_form_screen import build_character_form
        dialog = build_character_form(page, character=None, on_saved=lambda ch: refresh_grid())
        page.show_dialog(dialog)

    def _open_character_detail(char: Character):
        from .character_detail_screen import build_character_detail
        dialog = build_character_detail(
            page, char,
            on_saved=lambda ch: refresh_grid(),
            on_chat_started=lambda s: refresh_grid(),
        )
        page.show_dialog(dialog)

    def _delete_character(char: Character):
        def confirm_delete(e):
            storage.delete_character(char.id)
            page.pop_dialog()
            refresh_grid()
            page.show_dialog(ft.SnackBar(
                content=ft.Text(f"'{char.name}' {t('deleted_simple')}", color=c["white"]),
                bgcolor=c["error"],
            ))

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"'{char.name}' {t('delete_confirm_title')}"),
            content=ft.Text(t("irreversible")),
            actions=[
                ft.TextButton(t("btn_cancel"), on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(t("btn_delete"), on_click=confirm_delete, bgcolor=c["error"], color=c["white"]),
            ],
            bgcolor=c["surface_alt"],
        )
        page.show_dialog(confirm_dialog)

    def _export_character(char: Character):
        card_data = char.to_sillytavern_v2()
        json_str = json.dumps(card_data, ensure_ascii=False, indent=2)
        export_path = os.path.join(os.path.expanduser("~"), f"{char.name}_v2.json")
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            page.show_dialog(ft.SnackBar(
                content=ft.Text(f"{t('export_ok')} {export_path}", color=c["white"]),
                bgcolor=c["success"],
            ))
        except Exception as ex:
            page.show_dialog(ft.SnackBar(content=ft.Text(f"{t('error_prefix')} {str(ex)}")))
        page.update()

    create_btn = ft.ElevatedButton(
        t("new_character"),
        on_click=_open_create_form,
        icon=ft.Icons.ADD,
        color=c["white"],
        bgcolor=c["primary"],
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=rd["btn_sm"])),
    )

    toolbar = ft.Container(
        content=ft.Row([create_btn], alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.Padding(sp[12], sp[8], sp[12], sp[4]),
    )

    refresh_grid()
    page._personai_refresh_gallery = refresh_grid

    return ft.Container(
        bgcolor=c["bg"],
        content=ft.Column(
            controls=[
                toolbar,
                ft.Divider(thickness=1, color=c["border_subtle"]),
                grid,
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )
