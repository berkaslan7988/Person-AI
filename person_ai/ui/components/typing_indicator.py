"""Person AI - Animated typing indicator (3-dot pulse)."""

import flet as ft
from ..app_state import state


def typing_indicator() -> ft.Container:
    """Animated 'yazıyor...' indicator — three pulsing dots next to avatar."""
    c = state.theme["colors"]
    sp = state.theme["spacing"]

    # Three small dots with staggered opacity animation
    dots = []
    for i in range(3):
        dot = ft.Container(
            width=8,
            height=8,
            border_radius=4,
            bgcolor=c["primary"],
            opacity=0.3,
            animate_opacity=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT),
        )
        dots.append(dot)

    container = ft.Container(
        content=ft.Row(dots, spacing=sp[4]),
        visible=False,
    )

    # Store dot refs for external animation control
    container._dots = dots

    return container