"""Person AI - Settings section header component."""

import flet as ft
from ..app_state import state


def make_section_title(icon: ft.Icons, text: str) -> ft.Container:
    """Build a section header with icon + text for settings panels."""
    t = state.theme
    c = t["colors"]
    ty = t["typography"]

    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, color=c["primary"], size=20),
                ft.Text(
                    text,
                    size=ty["h2"][0],
                    weight=ft.FontWeight.BOLD,
                    color=c["text_primary"],
                ),
            ],
            spacing=t["spacing"][8],
        ),
        padding=ft.Padding(
            0, t["spacing"][12], 0, t["spacing"][4]
        ),
    )