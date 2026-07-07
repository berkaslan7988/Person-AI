"""Person AI - Main application shell (page setup + tab routing).

Features:
- Smooth tab transitions (fade)
- Skeleton shimmer loading
- Splash screen
- Onboarding wizard (first launch)
- Instant language / theme switching (full UI rebuild)
"""

import asyncio

import flet as ft
from .config import get_usable_models
from .ui.app_state import state
from .ui.screens.chat_screen import build_chat_screen
from .ui.screens.settings_screen import build_settings_screen
from .ui.screens.character_gallery_screen import build_character_gallery_screen
from .services.storage import storage
from .i18n import t


def main(page: ft.Page):
    """Flet entry point — sets up window, theme, tab routing."""
    # ── Restore persisted settings (language, theme, model, params) ──
    state.load_persisted_settings()

    th = state.theme
    c = th["colors"]
    sp = th["spacing"]
    rd = th["radius"]
    ty = th["typography"]
    win = th["window"]

    # ── Window config ──────────────────────────────────────────
    page.title = "Person AI"
    page.window.width = win["width"]
    page.window.height = win["height"]
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

    def _apply_page_theme():
        """Sync page-level colors with the current state.theme."""
        cc = state.theme["colors"]
        page.bgcolor = cc["bg"]
        page.theme_mode = {
            "light": ft.ThemeMode.LIGHT,
            "system": ft.ThemeMode.SYSTEM,
        }.get(state.theme_mode, ft.ThemeMode.DARK)
        if page.appbar:
            page.appbar.bgcolor = cc["surface_alt"]
            if isinstance(page.appbar.title, ft.Text):
                page.appbar.title.color = cc["text_primary"]

    _apply_page_theme()

    # ── Populate usable models ────────────────────────────────
    state.usable_models = get_usable_models()
    if state.selected_model not in state.usable_models:
        state.selected_model = state.usable_models[0] if state.usable_models else ""

    # ── Load last session on startup ──────────────────────────
    loaded = state.load_last_or_create()
    page._personai_restore_chat = bool(loaded and state.session.messages)

    # ── Splash screen ─────────────────────────────────────────
    splash = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Image(
                        src="icon.png",
                        width=96, height=96,
                        fit="contain",
                    ),
                    padding=sp[16],
                ),
                ft.Text(
                    "Person AI", size=24, weight=ft.FontWeight.BOLD,
                    color=c["primary"],
                ),
                ft.Text(
                    t("splash_subtitle"), size=14, color=c["text_secondary"],
                ),
                ft.ProgressBar(width=160, color=c["primary"], bgcolor=c["surface_alt"]),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=sp[12],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=c["bg"],
        alignment=ft.Alignment(0, 0),
        expand=True,
        animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
    )
    page.add(splash)
    page.update()

    # ── Skeleton loading ──────────────────────────────────────

    def _build_skeleton():
        """Build a shimmer skeleton while real UI initializes."""
        sk = ft.Column(spacing=sp[12], expand=True)
        for _ in range(5):
            sk.controls.append(
                ft.Container(
                    height=60,
                    bgcolor=c["surface_alt"],
                    border_radius=rd["card"],
                    padding=sp[12],
                    content=ft.Row([
                        ft.Container(
                            width=40, height=40, border_radius=20,
                            bgcolor=c["border"],
                        ),
                        ft.Column([
                            ft.Container(width=160, height=12, bgcolor=c["border"], border_radius=6),
                            ft.Container(width=100, height=8, bgcolor=c["border"], border_radius=4),
                        ], spacing=sp[4]),
                    ], spacing=sp[8]),
                )
            )
        return ft.Container(
            content=sk,
            padding=ft.Padding(sp[12], sp[16], sp[12], sp[12]),
            expand=True,
        )

    skeleton = _build_skeleton()
    skeleton.visible = False

    # ── Build screens (lazy, cached) ──────────────────────────
    chat_screen = None
    settings_screen = None
    gallery_screen = None
    current_tab = [0]

    def get_chat_screen():
        nonlocal chat_screen
        if chat_screen is None:
            chat_screen = build_chat_screen(page)
        return chat_screen

    def get_settings_screen():
        nonlocal settings_screen
        if settings_screen is None:
            settings_screen = build_settings_screen(page)
        return settings_screen

    def get_gallery_screen():
        nonlocal gallery_screen
        if gallery_screen is None:
            gallery_screen = build_character_gallery_screen(page)
        return gallery_screen

    # ── Tab switching ─────────────────────────────────────────
    page._personai_show_chat = lambda: switch_tab(0)
    page._personai_show_settings = lambda: switch_tab(1)
    page._personai_show_gallery = lambda: switch_tab(2)

    # ── Tab bar (rebuildable — labels follow the active language) ──
    def _make_tab_btn(icon, label, index, active=False):
        cc = state.theme["colors"]
        return ft.Container(
            content=ft.Row([
                ft.Icon(
                    icon, color=cc["white"] if active else cc["text_secondary"], size=18,
                ),
                ft.Text(
                    label, color=cc["white"] if active else cc["text_secondary"],
                    weight=ft.FontWeight.BOLD, size=ty["body"][0],
                ),
            ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=cc["primary"] if active else cc["surface_alt"],
            border_radius=rd["tab"],
            padding=ft.Padding(sp[16], sp[8], sp[16], sp[8]),
            on_click=lambda e: switch_tab(index),
            expand=True,
        )

    tab_row = ft.Row([], spacing=sp[4])

    def _rebuild_tab_bar(active_index: int):
        tabs = [
            (ft.Icons.CHAT_BUBBLE_OUTLINE, t("tab_chat")),
            (ft.Icons.SETTINGS, t("tab_settings")),
            (ft.Icons.PEOPLE, t("tab_characters")),
        ]
        tab_row.controls = [
            _make_tab_btn(icon, label, i, active=(i == active_index))
            for i, (icon, label) in enumerate(tabs)
        ]
        tab_bar.bgcolor = state.theme["colors"]["surface"]

    tab_bar = ft.Container(
        content=tab_row,
        bgcolor=c["surface"],
        padding=ft.Padding(sp[8], sp[4], sp[8], sp[4]),
    )
    _rebuild_tab_bar(0)

    # ── Content area ──────────────────────────────────────────
    content_area = ft.Stack(controls=[], expand=True)

    main_layout = ft.Column(
        [tab_bar, content_area], expand=True, spacing=0,
    )
    main_layout.visible = False
    page.add(main_layout)
    page.add(skeleton)

    def _mount_screens(active_index: int):
        """(Re)build all screens and show the one at active_index."""
        chat = get_chat_screen()
        settings = get_settings_screen()
        gallery = get_gallery_screen()

        for i, scr in enumerate([chat, settings, gallery]):
            scr.visible = (i == active_index)
            scr.animate_opacity = ft.Animation(300, ft.AnimationCurve.EASE_OUT)
        settings.expand = True
        gallery.expand = True

        content_area.controls = [chat, settings, gallery]
        _rebuild_tab_bar(active_index)
        current_tab[0] = active_index

    # ── Full UI rebuild (language / theme change) ─────────────
    _rebuilding = [False]

    async def _do_rebuild(active_index: int):
        """Two-phase rebuild: first detach the old screens and flush,
        then mount fresh ones. Keeps client patches small and consistent."""
        nonlocal chat_screen, settings_screen, gallery_screen
        if _rebuilding[0]:
            return
        _rebuilding[0] = True
        try:
            # Phase 1: detach old subtree
            content_area.controls = []
            page.update()
            await asyncio.sleep(0.05)

            # Phase 2: rebuild with current language/theme
            chat_screen = None
            settings_screen = None
            gallery_screen = None
            _apply_page_theme()
            _mount_screens(active_index)
            page.update()
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            _rebuilding[0] = False

    def rebuild_ui(active_index: int = None):
        """Rebuild the whole UI with the current language + theme.
        Deferred to a task so the originating event handler returns
        before its own subtree is replaced."""
        idx = current_tab[0] if active_index is None else active_index
        try:
            page.run_task(_do_rebuild, idx)
        except Exception:
            import traceback
            traceback.print_exc()

    page._personai_rebuild_ui = rebuild_ui

    # ── Build screens after splash ───────────────────────────

    async def init_after_splash():
        # Show splash for 1.5s then fade out
        try:
            await asyncio.sleep(1.5)
            splash.opacity = 0
            page.update()
            await asyncio.sleep(0.4)

            # Switch to skeleton
            splash.visible = False
            skeleton.visible = True
            page.update()
        except RuntimeError:
            return  # session closed while splash was showing — exit quietly

        try:
            _mount_screens(0)

            skeleton.visible = False
            main_layout.visible = True
            page.update()

            # No usable API key yet → guide the user to Settings
            if not state.usable_models:
                switch_tab(1)

            await _maybe_show_onboarding(page)
        except Exception as ex:
            skeleton.visible = False
            page.add(ft.Container(
                content=ft.Column([
                    ft.Text(t("init_error"), size=16, weight=ft.FontWeight.BOLD, color=c["error"]),
                    ft.Text(str(ex), size=12, color=c["text_secondary"], selectable=True),
                ], spacing=8),
                padding=sp[16],
            ))
            page.update()

    async def _maybe_show_onboarding(page: ft.Page):
        """Show onboarding wizard on first launch."""
        seen = storage.get_state("onboarding_seen", "")
        if seen == "1":
            return

        steps = [
            {"icon": ft.Icons.CHAT_BUBBLE_OUTLINE, "title": t("ob1_title"), "desc": t("ob1_desc")},
            {"icon": ft.Icons.PEOPLE, "title": t("ob2_title"), "desc": t("ob2_desc")},
            {"icon": ft.Icons.TUNE, "title": t("ob3_title"), "desc": t("ob3_desc")},
        ]

        current = [0]

        def _build_onboarding():
            step = steps[current[0]]
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Icon(step["icon"], size=64, color=c["primary"]),
                            alignment=ft.Alignment(0, 0),
                            padding=sp[16],
                        ),
                        ft.Text(step["title"], size=ty["h1"][0], weight=ft.FontWeight.BOLD, color=c["text_primary"]),
                        ft.Text(step["desc"], size=ty["body"][0], color=c["text_secondary"], text_align=ft.TextAlign.CENTER),
                        ft.Row(
                            [
                                ft.TextButton(
                                    t("ob_skip"),
                                    on_click=lambda e: _finish_onboarding(),
                                ),
                                ft.ElevatedButton(
                                    t("ob_next") if current[0] < len(steps) - 1 else t("ob_start"),
                                    on_click=lambda e: _next_step(),
                                    bgcolor=c["primary"], color=c["white"],
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    width=8, height=8, border_radius=4,
                                    bgcolor=c["primary"] if i == current[0] else c["border"],
                                )
                                for i in range(len(steps))
                            ],
                            spacing=sp[8],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=sp[16],
                ),
                bgcolor=c["bg"],
                expand=True,
                alignment=ft.Alignment(0, 0),
                padding=sp[24],
                animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            )

        def _next_step():
            current[0] += 1
            if current[0] >= len(steps):
                _finish_onboarding()
            else:
                onboarding_dialog.content = _build_onboarding()
                page.update()

        def _finish_onboarding():
            storage.set_state("onboarding_seen", "1")
            page.pop_dialog()

        onboarding_dialog = ft.AlertDialog(
            content=_build_onboarding(),
            bgcolor=c["bg"],
            modal=True,
            inset_padding=ft.Padding(sp[16], sp[16], sp[16], sp[16]),
        )
        page.show_dialog(onboarding_dialog)

    page.run_task(init_after_splash)

    # ── Animated tab switching (fade) ─────────────────────────

    def switch_tab(index: int):
        chat = get_chat_screen()
        settings = get_settings_screen()
        gallery = get_gallery_screen()

        screens = [chat, settings, gallery]
        # Fade out all screens
        for s in screens:
            s.opacity = 0
        page.update()

        def _swap_after_fade():
            for i, s in enumerate(screens):
                s.visible = (i == index)
                s.opacity = 1

            _rebuild_tab_bar(index)
            current_tab[0] = index
            page.bgcolor = state.theme["colors"]["bg"]

            if index == 0 and hasattr(page, "_personai_update_header"):
                page._personai_update_header()
            if index == 2 and hasattr(page, "_personai_refresh_gallery"):
                page._personai_refresh_gallery()

            page.update()

        # Small delay for fade-out effect, then fade-in
        async def _delayed_swap():
            await asyncio.sleep(0.15)
            _swap_after_fade()

        try:
            page.run_task(_delayed_swap)
        except Exception:
            _swap_after_fade()

    # ── App bar ───────────────────────────────────────────────
    page.appbar = ft.AppBar(
        title=ft.Text(
            "Person AI",
            weight=ft.FontWeight.BOLD,
            size=ty["h2"][0],
            color=c["text_primary"],
        ),
        center_title=True,
        bgcolor=c["surface_alt"],
    )
