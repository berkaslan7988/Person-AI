"""Person AI - Enhanced character card with avatar, summary, and actions."""

import flet as ft
from ...models.character import Character
from ..app_state import state
from ...i18n import t as tr


def character_card(
    character: Character,
    last_session_summary: str = "",
    on_tap: callable = None,
    on_new_chat: callable = None,
) -> ft.Container:
    """Build a character card for the gallery grid."""
    t = state.theme
    c = t["colors"]
    sp = t["spacing"]

    # Avatar
    if character.avatar_url:
        avatar = ft.Container(
            content=ft.Image(
                src=character.avatar_url,
                width=80, height=80,
                fit="cover",
                border_radius=40,
            ),
            alignment=ft.Alignment(0, -1),
            padding=ft.Padding(0, sp[8], 0, sp[4]),
        )
    else:
        avatar = ft.Container(
            content=ft.Icon(ft.Icons.PERSON, size=40, color=c["primary"]),
            width=80, height=80,
            border_radius=40,
            bgcolor=c["surface_alt"],
            alignment=ft.Alignment(0, 0),
            padding=ft.Padding(0, sp[8], 0, sp[4]),
        )

    # Name
    name_text = ft.Text(
        character.name,
        size=15,
        weight=ft.FontWeight.BOLD,
        color=c["text_primary"],
        text_align=ft.TextAlign.CENTER,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    # Traits summary
    summary = character.traits[:120] + "..." if len(character.traits) > 120 else character.traits
    trait_text = ft.Text(
        summary,
        size=11,
        color=c["text_secondary"],
        text_align=ft.TextAlign.CENTER,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    # Last session line
    session_line = ft.Text(
        last_session_summary or tr("new_chat"),
        size=10,
        color=c["primary_variant"] if last_session_summary else c["text_secondary"],
        text_align=ft.TextAlign.CENTER,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        italic=bool(last_session_summary),
    )

    # New chat button
    new_chat_btn = ft.IconButton(
        icon=ft.Icons.ADD_COMMENT,
        icon_size=16,
        icon_color=c["primary"],
        tooltip=tr("new_chat_tooltip"),
        on_click=on_new_chat,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    [ft.Container(width=24), name_text, new_chat_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                avatar,
                trait_text,
                ft.Divider(thickness=1, color=c["border_subtle"], height=1),
                ft.Container(
                    content=session_line,
                    padding=ft.Padding(sp[8], 0, sp[8], sp[4]),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        ),
        bgcolor=c["surface_alt"],
        border=ft.Border(
            ft.BorderSide(1, c["border"]),
            ft.BorderSide(1, c["border"]),
            ft.BorderSide(1, c["border"]),
            ft.BorderSide(1, c["border"]),
        ),
        border_radius=t["radius"]["card"],
        width=180,
        height=220,
        on_click=on_tap,
        ink=True,
    )
