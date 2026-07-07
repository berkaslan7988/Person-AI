"""Chat bubble — uses Flet's data pattern for reliable web event handling.

Instead of closures (which Flet web doesn't fire reliably), each action button
stores its payload in control.data and a module-level handler reads it via
e.control.data and e.control.page.  This is the idiomatic Flet pattern.
"""

import re
import logging
import traceback
import flet as ft
from ..app_state import state

logger = logging.getLogger("person_ai.bubble")
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def _t(key: str) -> str:
    """Late import to avoid a circular dependency at module load."""
    from ...i18n import t
    return t(key)


# ── Markdown-lite RP formatter ────────────────────────────────

def _parse_rp_markdown(text: str) -> list[ft.TextSpan]:
    c = state.theme["colors"]
    pattern = re.compile(
        r"(\*\*(.+?)\*\*)"
        r"|(\*(.+?)\*)"
        r"|(`(.+?)`)"
    )
    spans: list[ft.TextSpan] = []
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            spans.append(ft.TextSpan(text=text[last:m.start()]))
        if m.group(1):
            spans.append(ft.TextSpan(
                text=m.group(2),
                style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            ))
        elif m.group(3):
            spans.append(ft.TextSpan(
                text=m.group(4),
                style=ft.TextStyle(italic=True, color=c["text_secondary"]),
            ))
        elif m.group(5):
            spans.append(ft.TextSpan(
                text=m.group(6),
                style=ft.TextStyle(font_family="monospace"),
            ))
        last = m.end()
    if last < len(text):
        spans.append(ft.TextSpan(text=text[last:]))
    return spans if spans else [ft.TextSpan(text=text)]


# ── Module-level event handlers ───────────────────────────────

def _on_copy(e: ft.ControlEvent):
    logger.info(f"[BTN] copy clicked  data={e.control.data!r}")
    try:
        payload = e.control.data
        text = payload["text"] if isinstance(payload, dict) else str(payload)
        page = e.control.page
        try:
            page.set_clipboard(text)
            ok = True
        except Exception as ex:
            logger.warning(f"[BTN] set_clipboard failed: {ex}")
            ok = False
        c = state.theme["colors"]
        try:
            page.show_dialog(ft.SnackBar(
                content=ft.Text(_t("copied") if ok else _t("copy_failed"),
                                color=c["white"]),
                bgcolor=c["success"] if ok else c["error"],
            ))
        except Exception as ex:
            logger.warning(f"[BTN] toast failed: {ex}")
    except Exception:
        logger.error(f"[BTN] copy handler crashed:\n{traceback.format_exc()}")


def _on_edit(e: ft.ControlEvent):
    logger.info(f"[BTN] edit  clicked  data={e.control.data!r}  _cb_edit={state._cb_edit!r}")
    try:
        idx = int(e.control.data)
        if state._cb_edit:
            state._cb_edit(idx)
            logger.info(f"[BTN] edit({idx}) done")
        else:
            logger.warning("[BTN] _cb_edit is None — build_chat_screen not called yet?")
    except Exception:
        logger.error(f"[BTN] edit handler crashed:\n{traceback.format_exc()}")


def _on_delete(e: ft.ControlEvent):
    logger.info(f"[BTN] delete clicked  data={e.control.data!r}  _cb_delete={state._cb_delete!r}")
    try:
        idx = int(e.control.data)
        if state._cb_delete:
            state._cb_delete(idx)
            logger.info(f"[BTN] delete({idx}) done")
        else:
            logger.warning("[BTN] _cb_delete is None — build_chat_screen not called yet?")
    except Exception:
        logger.error(f"[BTN] delete handler crashed:\n{traceback.format_exc()}")


def _on_regen(e: ft.ControlEvent):
    logger.info(f"[BTN] regen  clicked  data={e.control.data!r}  _cb_regen={state._cb_regenerate!r}")
    try:
        idx = int(e.control.data)
        if state._cb_regenerate:
            state._cb_regenerate(idx)
            logger.info(f"[BTN] regen({idx}) done")
        else:
            logger.warning("[BTN] _cb_regenerate is None — build_chat_screen not called yet?")
    except Exception:
        logger.error(f"[BTN] regen handler crashed:\n{traceback.format_exc()}")


# ── Avatar ───────────────────────────────────────────────────

def _build_avatar(is_user: bool, size: int = 34) -> ft.Container:
    c = state.theme["colors"]
    url = state.user_avatar_url if is_user else state.avatar_url
    if url:
        return ft.Container(
            content=ft.Image(src=url, fit=ft.BoxFit.COVER,
                             width=size, height=size),
            width=size, height=size,
            border_radius=size // 2,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
    icon_name = ft.Icons.PERSON if is_user else ft.Icons.SMART_TOY
    bg = c["user_bubble"] if is_user else c["ai_bubble"]
    icon_color = (c.get("bubble_text_user", c["white"]) if is_user
                  else c.get("bubble_text_ai", c["white"]))
    return ft.Container(
        content=ft.Icon(icon_name, size=size - 14, color=icon_color),
        width=size, height=size,
        border_radius=size // 2,
        bgcolor=bg,
        alignment=ft.Alignment(0, 0),
    )


# ── Action bar ───────────────────────────────────────────────
# ft.IconButton does NOT fire inside ListView in Flet web mode.
# ft.Container(on_click=..., ink=True) creates a Flutter InkWell
# which fires reliably everywhere.

def _make_btn(icon, color, data, handler, tooltip="") -> ft.Container:
    return ft.Container(
        content=ft.Icon(icon, size=16, color=color),
        data=data,
        on_click=handler,
        ink=True,
        padding=ft.Padding(6, 6, 6, 6),
        border_radius=ft.BorderRadius(20, 20, 20, 20),
        tooltip=tooltip,
    )


def _build_actions(role: str, index: int, text: str) -> ft.Row:
    c   = state.theme["colors"]
    sec = c["text_secondary"]

    # copy button uses dict payload to carry the text
    btns = [_make_btn(
        ft.Icons.CONTENT_COPY, sec,
        {"text": text, "index": index},
        _on_copy, _t("tooltip_copy"),
    )]

    if role != "user":
        btns.append(_make_btn(
            ft.Icons.REFRESH, c["primary_variant"],
            index, _on_regen, _t("tooltip_regen"),
        ))

    btns += [
        _make_btn(ft.Icons.EDIT_OUTLINED, sec,    index, _on_edit,   _t("tooltip_edit")),
        _make_btn(ft.Icons.DELETE_OUTLINE, c["error"], index, _on_delete, _t("tooltip_delete")),
    ]

    return ft.Row(
        btns, spacing=0,
        alignment=(ft.MainAxisAlignment.END if role == "user"
                   else ft.MainAxisAlignment.START),
    )


# ── Bubble builder ───────────────────────────────────────────

def chat_bubble(
    role: str,
    text: str,
    index: int,
    page: ft.Page = None,        # kept for API compat, unused
    chat_list=None,              # kept for API compat, unused
    on_regenerate=None,          # kept for API compat, unused
    is_last: bool = False,
) -> ft.Container:
    t  = state.theme
    c  = t["colors"]
    rd = t["radius"]
    is_user = role == "user"

    avatar = _build_avatar(is_user)

    bubble = ft.Container(
        content=ft.Text(
            spans=_parse_rp_markdown(text),
            selectable=True,
            size=t["typography"]["body"][0],
            color=(c.get("bubble_text_user", c["white"]) if is_user
                   else c.get("bubble_text_ai", c["white"])),
        ),
        bgcolor=c["user_bubble"] if is_user else c["ai_bubble"],
        padding=ft.Padding(14, 10, 14, 10),
        border_radius=ft.BorderRadius(
            top_left=rd["bubble"] if is_user else 6,
            top_right=6 if is_user else rd["bubble"],
            bottom_left=rd["bubble"],
            bottom_right=rd["bubble"],
        ),
    )

    actions = _build_actions(role, index, text)

    bubble_col = ft.Column(
        [bubble, actions],
        spacing=2,
        expand=True,
        horizontal_alignment=(ft.CrossAxisAlignment.END if is_user
                               else ft.CrossAxisAlignment.START),
    )

    row_controls = ([bubble_col, avatar] if is_user
                    else [avatar, bubble_col])

    wrapper = ft.Container(
        content=ft.Row(
            row_controls,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=8,
        ),
        padding=ft.Padding(8, 3, 8, 3),
    )
    wrapper.data = {"role": role, "index": index}
    return wrapper


def add_bubble(chat_list, role: str, text: str,
               page: ft.Page = None, on_regenerate=None):
    """Append one bubble (kept for compatibility)."""
    index = len(chat_list.controls)
    chat_list.controls.append(
        chat_bubble(role, text, index)
    )
    if page:
        page.update()
