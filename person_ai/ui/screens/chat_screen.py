"""Person AI - Chat screen (rebuilt).

Key design: chat_list.controls is always rebuilt from state.session.messages
via render_all(), so message indices are always correct and every bubble's
action buttons (copy / edit / delete / regenerate) operate on the right item.
"""

import asyncio
import flet as ft
from ..app_state import state
from ..components.chat_bubble import chat_bubble, _parse_rp_markdown
from ..components.typing_indicator import typing_indicator
from ...services.ai_providers import generate_response, ProviderRateLimitError
from ...services.streaming import STREAM_PROVIDERS, stream_response
from ...config import AVAILABLE_MODELS
from ...i18n import t as tr


def build_chat_screen(page: ft.Page) -> ft.Column:
    t = state.theme
    c = t["colors"]
    sp = t["spacing"]
    rd = t["radius"]
    ty = t["typography"]

    # ── Header bar ─────────────────────────────────────────────
    header_avatar = ft.Container(
        width=38, height=38,
        border_radius=19,
        bgcolor=c["ai_bubble"],
        alignment=ft.Alignment(0, 0),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Icon(ft.Icons.SMART_TOY, size=20, color=c.get("bubble_text_ai", c["white"])),
    )
    header_name = ft.Text(
        state.character.name, size=ty["h2"][0],
        weight=ft.FontWeight.BOLD, color=c["text_primary"],
    )
    model_badge = ft.Container(
        content=ft.Text("", size=ty["caption"][0], color=c["primary_variant"]),
        bgcolor=c["surface_alt"], border_radius=8,
        padding=ft.Padding(sp[8], 2, sp[8], 2),
    )

    def _refresh_avatar():
        if state.avatar_url:
            header_avatar.bgcolor = None
            header_avatar.content = ft.Image(
                src=state.avatar_url, fit=ft.BoxFit.COVER, width=38, height=38,
            )
        else:
            header_avatar.bgcolor = c["ai_bubble"]
            header_avatar.content = ft.Icon(ft.Icons.SMART_TOY, size=20, color=c.get("bubble_text_ai", c["white"]))

    def update_header():
        header_name.value = state.character.name
        model_badge.content.value = state.selected_model or ""
        _refresh_avatar()
        if state.chat_background_url:
            chat_bg_wrapper.image = ft.DecorationImage(src=state.chat_background_url, fit=ft.BoxFit.COVER)
            chat_bg_wrapper.bgcolor = None
        else:
            chat_bg_wrapper.image = None
            chat_bg_wrapper.bgcolor = c["bg"]
        _update_empty_state()
        page.update()

    def _clear_chat(e=None):
        def confirm(e2):
            state.session.messages.clear()
            state.session.id = None
            state._auto_save()
            page.pop_dialog()
            render_all(scroll=False)
            page.show_dialog(ft.SnackBar(
                content=ft.Text(tr("chat_cleared"), color=c["white"]),
                bgcolor=c["success"],
            ))
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(tr("clear_chat_title")),
            content=ft.Text(tr("clear_chat_body")),
            actions=[
                ft.TextButton(tr("btn_cancel"), on_click=lambda e: page.pop_dialog()),
                ft.ElevatedButton(tr("btn_clear"), on_click=confirm,
                                  bgcolor=c["error"], color=c["white"]),
            ],
            bgcolor=c["surface_alt"],
        ))

    clear_btn = ft.Container(
        content=ft.Icon(ft.Icons.DELETE_SWEEP_OUTLINED, size=20, color=c["text_secondary"]),
        on_click=_clear_chat,
        ink=True,
        padding=ft.Padding(6, 6, 6, 6),
        border_radius=ft.BorderRadius(20, 20, 20, 20),
        tooltip=tr("clear_chat_tooltip"),
    )

    header_row = ft.Container(
        content=ft.Row(
            [header_avatar,
             ft.Column([header_name, model_badge], spacing=2, expand=True),
             clear_btn],
            spacing=sp[8],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(sp[12], sp[8], sp[12], sp[8]),
        bgcolor=c["surface"],
    )

    # ── Chat list ──────────────────────────────────────────────
    chat_list = ft.ListView(
        expand=True, spacing=4, auto_scroll=False,
        padding=ft.Padding(sp[8], sp[12], sp[8], sp[12]),
    )

    async def _scroll_to_bottom():
        try:
            if chat_list.controls:
                await chat_list.scroll_to(offset=-1, duration=250)
        except Exception:
            pass
        scroll_btn.visible = False
        page.update()

    def _on_scroll(e):
        try:
            if e.pixels is not None and e.max_scroll_extent is not None:
                scroll_btn.visible = (e.max_scroll_extent - e.pixels) > 220
                scroll_btn.update()
        except Exception:
            pass

    chat_list.on_scroll = _on_scroll

    scroll_btn = ft.FloatingActionButton(
        icon=ft.Icons.KEYBOARD_ARROW_DOWN, mini=True,
        bgcolor=c["primary"], visible=False,
        on_click=lambda e: page.run_task(_scroll_to_bottom),
        tooltip=tr("scroll_down"),
    )

    # ── Empty state ────────────────────────────────────────────
    empty_title = ft.Text(
        state.character.name, size=ty["h1"][0], weight=ft.FontWeight.BOLD,
        color=c["text_primary"], text_align=ft.TextAlign.CENTER,
    )
    empty_traits = ft.Text(
        "", size=ty["body"][0], color=c["text_secondary"],
        text_align=ft.TextAlign.CENTER, max_lines=6,
    )
    empty_greet = ft.Text(
        "", size=ty["body"][0], color=c["primary_variant"],
        italic=True, text_align=ft.TextAlign.CENTER,
    )
    empty_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.AUTO_AWESOME, size=52, color=c["primary"]),
                    alignment=ft.Alignment(0, 0), padding=sp[12],
                ),
                empty_title, empty_traits,
                ft.Container(content=empty_greet, padding=ft.Padding(sp[8], sp[16], sp[8], sp[16])),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=sp[8],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.Alignment(0, 0), padding=sp[24], visible=True,
    )

    def _update_empty_state():
        has_msgs = len(state.session.messages) > 0
        empty_container.visible = not has_msgs
        empty_title.value = state.character.name
        trts = state.character.traits or ""
        empty_traits.value = (trts[:160] + "...") if len(trts) > 160 else trts
        empty_greet.value = state.character.greeting or f"{tr('greeting_default')} {state.character.name}. {tr('greeting_start')}"

    # ── Typing indicator ──────────────────────────────────────
    typing = typing_indicator()

    # ── Edit banner + input ───────────────────────────────────
    edit_index = [None]

    edit_banner = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.EDIT, size=14, color=c["primary_variant"]),
                ft.Text(tr("editing_message"), size=12, color=c["primary_variant"], expand=True),
                ft.IconButton(
                    icon=ft.Icons.CLOSE, icon_size=16, icon_color=c["text_secondary"],
                    tooltip=tr("btn_cancel"), on_click=lambda e: _cancel_edit(),
                ),
            ],
            spacing=sp[8],
        ),
        bgcolor=c["surface_alt"],
        padding=ft.Padding(sp[12], sp[4], sp[4], sp[4]),
        visible=False,
    )

    _no_key = not state.usable_models
    user_input_field = ft.TextField(
        hint_text=tr("no_key_hint") if _no_key else tr("type_message"),
        expand=True,
        border_radius=rd["bubble"], shift_enter=True, multiline=True,
        min_lines=1, max_lines=5,
        on_submit=lambda e: page.run_task(send_message_dispatch),
        bgcolor=c["surface_alt"], border_color=c["border"],
        focused_border_color=c["primary"], cursor_color=c["primary"],
        text_size=ty["body"][0],
    )

    def _edit_message(idx: int, text: str = ""):
        if not (0 <= idx < len(state.session.messages)):
            return
        edit_index[0] = idx
        user_input_field.value = state.session.messages[idx].content
        edit_banner.visible = True
        user_input_field.focus()
        page.update()

    def _cancel_edit():
        edit_index[0] = None
        user_input_field.value = ""
        edit_banner.visible = False
        page.update()

    # ── Rendering: single source of truth ─────────────────────
    def render_all(scroll: bool = True):
        chat_list.controls.clear()
        msgs = state.session.messages
        if not msgs:
            _update_empty_state()
            chat_list.controls.append(
                ft.Container(
                    content=empty_container,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(16, 32, 16, 16),
                    height=420,
                )
            )
        else:
            for i, msg in enumerate(msgs):
                chat_list.controls.append(
                    chat_bubble(msg.role, msg.content, i,
                                is_last=(i == len(msgs) - 1))
                )
        page.update()
        if scroll:
            page.run_task(_scroll_to_bottom)

    # ── Typing animation ──────────────────────────────────────
    async def _start_typing_animation():
        dots = getattr(typing, "_dots", None)
        if not dots:
            return
        typing.visible = True
        page.update()
        import itertools
        for i in itertools.cycle(range(3)):
            if not typing.visible:
                break
            for j, dot in enumerate(dots):
                dot.opacity = 1.0 if j == i else 0.3
                try:
                    dot.update()
                except Exception:
                    pass
            await asyncio.sleep(0.35)

    def _stop_typing_animation():
        typing.visible = False
        page.update()

    # ── Live streaming bubble ─────────────────────────────────
    async def _stream_reply(provider, model_id, messages, sys_inst, temp) -> str:
        live_text = ft.Text(
            "", size=ty["body"][0],
            color=c.get("bubble_text_ai", c["white"]), selectable=True,
        )
        live_avatar = ft.Container(
            width=34, height=34, border_radius=17, bgcolor=c["ai_bubble"],
            alignment=ft.Alignment(0, 0),
            content=ft.Icon(ft.Icons.SMART_TOY, size=18, color=c.get("bubble_text_ai", c["white"])),
        )
        live_bubble_box = ft.Container(
            content=live_text, bgcolor=c["ai_bubble"],
            padding=ft.Padding(14, 10, 14, 10),
            border_radius=ft.BorderRadius(6, rd["bubble"], rd["bubble"], rd["bubble"]),
        )
        live_col = ft.Column([live_bubble_box], expand=True,
                             horizontal_alignment=ft.CrossAxisAlignment.START)
        live_bubble = ft.Container(
            content=ft.Row(
                [live_avatar, live_col],
                vertical_alignment=ft.CrossAxisAlignment.START, spacing=8,
            ),
            padding=ft.Padding(8, 3, 8, 3),
        )
        chat_list.controls.append(live_bubble)
        page.update()
        await asyncio.sleep(0.03)
        await _scroll_to_bottom()

        acc = []

        def cancel_check():
            return state.streaming_cancel

        gen = await asyncio.to_thread(
            stream_response, provider, model_id, messages, sys_inst, temp,
            cancel_flag=cancel_check,
        )
        for token in gen:
            if state.streaming_cancel:
                break
            acc.append(token)
            live_text.value = "".join(acc)
            if len(acc) % 4 == 0:
                page.update()
            if len(acc) % 16 == 0:
                try:
                    await chat_list.scroll_to(offset=-1, duration=0)
                except Exception:
                    pass
        return "".join(acc)

    # ── Core generation ───────────────────────────────────────
    async def _generate_reply():
        context_messages = state.recent_messages
        label = state.selected_model
        data = AVAILABLE_MODELS.get(label, {})
        provider = data.get("provider", "")
        model_id = data.get("id", "")
        sys_inst = state.effective_system_instruction

        try:
            if provider in STREAM_PROVIDERS:
                reply = await _stream_reply(provider, model_id, context_messages, sys_inst, state.temperature)
            else:
                reply = await asyncio.to_thread(
                    generate_response, provider=provider, model_id=model_id,
                    messages=context_messages, system_instruction=sys_inst,
                    temperature=state.temperature,
                )
            if reply and reply.strip():
                state.add_assistant_message(reply)
            return True
        except Exception as err:
            error_str = str(err).lower()
            is_rate = isinstance(err, ProviderRateLimitError) or any(
                k in error_str for k in ("429", "resource_exhausted", "rate limit")
            )
            if is_rate:
                for opt in state.usable_models:
                    if opt == label:
                        continue
                    fb = AVAILABLE_MODELS.get(opt, {})
                    try:
                        _toast_info(f"{tr('model_limit')} {opt}")
                        if fb.get("provider") in STREAM_PROVIDERS:
                            reply = await _stream_reply(fb["provider"], fb["id"], context_messages, sys_inst, state.temperature)
                        else:
                            reply = await asyncio.to_thread(
                                generate_response, provider=fb.get("provider"), model_id=fb.get("id"),
                                messages=context_messages, system_instruction=sys_inst,
                                temperature=state.temperature,
                            )
                        state.selected_model = opt
                        if reply and reply.strip():
                            state.add_assistant_message(reply)
                        return True
                    except Exception:
                        continue
                _toast_info(tr("all_models_failed"), ok=False)
                return False
            else:
                user_msg = getattr(err, "user_message", str(err))
                _toast_info(f"{tr('error_prefix')} {user_msg}", ok=False)
                return False

    def _toast_info(message: str, ok: bool = True):
        try:
            page.show_dialog(ft.SnackBar(
                content=ft.Text(message, color=c["white"]),
                bgcolor=c["success"] if ok else c["error"],
            ))
        except Exception:
            pass

    async def _run_generation():
        typing_task = asyncio.create_task(_start_typing_animation())
        state.streaming_cancel = False
        try:
            await _generate_reply()
        finally:
            state.streaming_cancel = True
            _stop_typing_animation()
            typing_task.cancel()
        state.streaming_cancel = False
        render_all()

    # ── Send / edit dispatch ──────────────────────────────────
    async def send_message_dispatch(e=None):
        text = (user_input_field.value or "").strip()
        if not text:
            return
        if not state.usable_models:
            _toast_info(tr("add_key_first"), ok=False)
            return

        # Editing an existing message
        if edit_index[0] is not None:
            idx = edit_index[0]
            edit_index[0] = None
            edit_banner.visible = False
            user_input_field.value = ""
            if 0 <= idx < len(state.session.messages):
                msg = state.session.messages[idx]
                msg.content = text
                if msg.role == "user":
                    # drop everything after and regenerate
                    del state.session.messages[idx + 1:]
                    state._auto_save()
                    render_all()
                    await _run_generation()
                else:
                    # AI message edited in place
                    state._auto_save()
                    render_all()
            return

        # Normal new message
        state.add_user_message(text)
        user_input_field.value = ""
        render_all()
        await _run_generation()

    # ── Mutations from bubble buttons ─────────────────────────
    def delete_message(idx: int):
        if 0 <= idx < len(state.session.messages):
            del state.session.messages[idx]
            state._auto_save()
            if edit_index[0] is not None:
                _cancel_edit()
            render_all(scroll=False)

    async def regenerate_at(idx: int):
        # Drop the AI message at idx and everything after it, then regenerate
        if not (0 <= idx < len(state.session.messages)):
            return
        del state.session.messages[idx:]
        # need a trailing user message to regenerate from
        if not state.session.messages or state.session.messages[-1].role != "user":
            state._auto_save()
            render_all(scroll=False)
            return
        state._auto_save()
        render_all()
        await _run_generation()

    # ── Input row ──────────────────────────────────────────────
    input_row = ft.Container(
        content=ft.Column(
            [
                edit_banner,
                ft.Row(
                    [
                        user_input_field, typing,
                        ft.IconButton(
                            icon=ft.Icons.SEND_ROUNDED, icon_color=c["primary"], icon_size=24,
                            on_click=lambda e: page.run_task(send_message_dispatch),
                            tooltip=tr("send"),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=0,
        ),
        padding=ft.Padding(sp[8], sp[4], sp[4], sp[8]),
        bgcolor=c["surface"],
    )

    # ── Chat area: Stack only for chat_list + FAB.
    # The empty state is inserted as the first item inside chat_list
    # so there is no covering/overlapping container that blocks click events.
    chat_area = ft.Stack(
        controls=[
            ft.Container(content=chat_list, left=0, top=0, right=0, bottom=0),
            ft.Container(content=scroll_btn, right=16, bottom=16),
        ],
        expand=True,
    )

    chat_bg_wrapper = ft.Container(
        content=chat_area, expand=True, bgcolor=c["bg"],
        image=(ft.DecorationImage(src=state.chat_background_url, fit=ft.BoxFit.COVER)
               if state.chat_background_url else None),
    )

    # ── Wire callbacks — stored on state (not page) so web mode can reach them ──
    state._cb_edit      = lambda idx: _edit_message(idx)
    state._cb_delete    = lambda idx: delete_message(idx)
    state._cb_regenerate = lambda idx: page.run_task(regenerate_at, idx)

    # Legacy page refs kept for other screens that do hasattr(page, ...) checks
    page._personai_chat_list    = chat_list
    page._personai_typing       = typing
    page._personai_header_name  = header_name
    page._personai_update_header = update_header
    page._personai_render_chat  = render_all
    page._personai_regenerate   = lambda: None

    # ── Restore messages on startup ───────────────────────────
    update_header()
    render_all(scroll=True)
    if getattr(page, "_personai_restore_chat", False):
        page._personai_restore_chat = False

    return ft.Column([header_row, chat_bg_wrapper, input_row], expand=True, spacing=0)
