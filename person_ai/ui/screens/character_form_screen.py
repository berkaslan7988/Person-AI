"""Person AI - Character create/edit form dialog.

Supports: name, traits, greeting, examples, tags, avatar URL.
"""
import flet as ft
from ..app_state import state
from ...models.character import Character
from ...services.storage import storage
from ...i18n import t


def build_character_form(
    page: ft.Page,
    character: Character = None,
    on_saved: callable = None,
) -> ft.AlertDialog:
    """Return an AlertDialog with the character form."""
    theme_c = state.theme["colors"]
    sp = state.theme["spacing"]
    rd = state.theme["radius"]
    ty = state.theme["typography"]

    is_edit = character is not None
    char = character or Character()

    # ── Form fields ─────────────────────────────────────────────
    name_field = ft.TextField(
        label=t("field_name"),
        value=char.name,
        border_color=theme_c["primary"],
        focused_border_color=theme_c["primary_variant"],
        text_size=ty["body"][0],
    )

    traits_field = ft.TextField(
        label=t("field_traits"),
        value=char.traits,
        multiline=True,
        min_lines=3,
        max_lines=8,
        border_color=theme_c["primary"],
        focused_border_color=theme_c["primary_variant"],
        text_size=ty["body"][0],
    )

    greeting_field = ft.TextField(
        label=t("field_greeting"),
        value=char.greeting,
        multiline=True,
        min_lines=2,
        max_lines=5,
        border_color=theme_c["primary"],
        focused_border_color=theme_c["primary_variant"],
        text_size=ty["body"][0],
        hint_text="...",
    )

    examples_field = ft.TextField(
        label=t("field_examples"),
        value="\n".join(char.examples),
        multiline=True,
        min_lines=3,
        max_lines=8,
        border_color=theme_c["primary"],
        focused_border_color=theme_c["primary_variant"],
        text_size=ty["body"][0],
        hint_text="#user: Hi\n#char: Hey! How are you?",
    )

    tags_field = ft.TextField(
        label=t("field_tags"),
        value=", ".join(char.tags),
        border_color=theme_c["primary"],
        focused_border_color=theme_c["primary_variant"],
        text_size=ty["body"][0],
        hint_text="romantic, comedy, sci-fi",
    )

    avatar_url_field = ft.TextField(
        label=t("field_avatar"),
        value=char.avatar_url,
        border_color=theme_c["primary"],
        focused_border_color=theme_c["primary_variant"],
        text_size=ty["body"][0],
    )

    # ── Save / Cancel ───────────────────────────────────────────

    def save_and_close(e):
        tags_raw = tags_field.value.strip()
        tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []
        examples_raw = examples_field.value.strip()
        examples = (
            [ln.strip() for ln in examples_raw.split("\n") if ln.strip()]
            if examples_raw else []
        )
        saved = Character(
            id=char.id,
            name=name_field.value.strip() or "Unnamed",
            traits=traits_field.value.strip(),
            greeting=greeting_field.value.strip(),
            avatar_url=avatar_url_field.value.strip(),
            examples=examples,
            tags=tags,
        )
        new_id = storage.save_character(saved)
        saved.id = new_id

        page.pop_dialog()
        if on_saved:
            on_saved(saved)
        page.show_dialog(ft.SnackBar(
            content=ft.Text(f"'{saved.name}' {t('char_saved')}", color=theme_c["white"]),
            bgcolor=theme_c["success"],
        ))

    def cancel(e):
        page.pop_dialog()

    # ── Build dialog ────────────────────────────────────────────
    dialog = ft.AlertDialog(
        title=ft.Text(
            t("form_title_edit") if is_edit else t("form_title_create"),
            weight=ft.FontWeight.BOLD,
            color=theme_c["text_primary"],
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    name_field,
                    traits_field,
                    greeting_field,
                    examples_field,
                    tags_field,
                    ft.Text(t("field_avatar_label"), size=ty["label"][0], color=theme_c["text_secondary"]),
                    avatar_url_field,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=sp[8],
            ),
            width=380,
            height=530,
        ),
        actions=[
            ft.TextButton(t("btn_cancel"), on_click=cancel),
            ft.ElevatedButton(
                t("btn_save"),
                on_click=save_and_close,
                bgcolor=theme_c["primary"],
                color=theme_c["white"],
            ),
        ],
        bgcolor=theme_c["surface_alt"],
    )

    return dialog
