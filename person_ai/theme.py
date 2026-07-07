"""Person AI — Centralised Design System.

All UI files import tokens from here — no hard-coded values.

Usage:
    from person_ai.theme import get_theme
    t = get_theme("dark")            # default palette
    t = get_theme("light", "#0ea5e9")  # light palette with custom accent
"""

# ═══════════════════════════════════════════════════════════════
#  RAW TOKEN DICTIONARIES (static)
# ═══════════════════════════════════════════════════════════════

# ── Colour Palette ─────────────────────────────────────────────

DARK_COLORS = {
    "bg": "#0a0a14",
    "surface": "#13131f",
    "surface_alt": "#1c1c2e",

    "primary": "#8b5cf6",
    "primary_variant": "#c4b5fd",

    "accent": "#fbbf24",

    "error": "#e5484d",
    "success": "#30a46c",

    "text_primary": "#ededf5",
    "text_secondary": "#9aa0b5",

    "border": "#2e2e48",
    "border_subtle": "#202034",

    "user_bubble": "#6d4ae0",
    "ai_bubble": "#24243a",
    "bubble_text_user": "#ffffff",
    "bubble_text_ai": "#ededf5",

    "white": "#ffffff",
    "black": "#000000",
}

LIGHT_COLORS = {
    "bg": "#f5f5fa",
    "surface": "#ffffff",
    "surface_alt": "#eeeeff",

    "primary": "#7c4dff",
    "primary_variant": "#5e35b1",

    "accent": "#ff6d00",

    "error": "#c62828",
    "success": "#2e7d32",

    "text_primary": "#1a1a2e",
    "text_secondary": "#555577",

    "border": "#ccccdd",
    "border_subtle": "#e0e0ee",

    "user_bubble": "#7c4dff",
    "ai_bubble": "#ffffff",
    "bubble_text_user": "#ffffff",
    "bubble_text_ai": "#1a1a2e",

    "white": "#ffffff",
    "black": "#000000",
}


# ── Accent presets (shown as swatches in Settings → Appearance) ─

ACCENT_PRESETS = [
    ("", "default"),        # falls back to the palette's own primary
    ("#8b5cf6", "purple"),
    ("#3b82f6", "blue"),
    ("#10b981", "green"),
    ("#f59e0b", "amber"),
    ("#ec4899", "pink"),
    ("#ef4444", "red"),
]


def _blend(hex_color: str, target: str, factor: float) -> str:
    """Blend hex_color towards target ("#ffffff" or "#000000") by factor 0..1."""
    try:
        hc = hex_color.lstrip("#")
        tc = target.lstrip("#")
        rgb = [int(hc[i:i + 2], 16) for i in (0, 2, 4)]
        tgt = [int(tc[i:i + 2], 16) for i in (0, 2, 4)]
        out = [round(a + (b - a) * factor) for a, b in zip(rgb, tgt)]
        return "#" + "".join(f"{v:02x}" for v in out)
    except (ValueError, IndexError):
        return hex_color


def lighten(hex_color: str, factor: float = 0.35) -> str:
    return _blend(hex_color, "#ffffff", factor)


def darken(hex_color: str, factor: float = 0.25) -> str:
    return _blend(hex_color, "#000000", factor)


# ── Typography Scale ───────────────────────────────────────────
# Format: { "key": (size, weight) }
# weight: "Bold" | "Medium" | "Regular"

TYPOGRAPHY = {
    "h1": (22, "Bold"),
    "h2": (18, "Bold"),
    "body": (14, "Regular"),
    "caption": (12, "Regular"),
    "label": (13, "Medium"),
}


def _ft_weight(name: str):
    """Convert string weight to flet FontWeight."""
    from flet import FontWeight
    return getattr(FontWeight, name.upper(), FontWeight.NORMAL)


# ── Spacing Scale ──────────────────────────────────────────────

SPACING = {
    4: 4,
    8: 8,
    12: 12,
    16: 16,
    24: 24,
    32: 32,
}

# Aliases for readability
SPACE = SPACING


# ── Border Radius Scale ───────────────────────────────────────

RADIUS = {
    "btn_sm": 8,    # small buttons
    "input": 12,    # text fields / dropdowns
    "card": 16,     # cards / containers
    "bubble": 24,   # chat bubbles / pill shapes
    "tab": 20,      # tab buttons
}


# ── Window ────────────────────────────────────────────────────

WINDOW = {
    "width": 420,
    "height": 820,
}


# ═══════════════════════════════════════════════════════════════
#  THEME HELPER
# ═══════════════════════════════════════════════════════════════

def get_theme(mode: str = "dark", accent: str = ""):
    """Return combined theme dict for the given mode and optional accent.

    Args:
        mode: "dark" | "light" | "system" (system falls back to dark palette;
              the OS-level widgets follow page.theme_mode)
        accent: optional hex color overriding the palette primary ("" = default)

    Returns dict with keys: colors, typography, spacing, radius, window, mode.
    """
    base = LIGHT_COLORS if mode == "light" else DARK_COLORS
    colors = dict(base)  # copy — never mutate module-level palettes

    if accent:
        colors["primary"] = accent
        if mode == "light":
            colors["primary_variant"] = darken(accent, 0.30)
            colors["user_bubble"] = accent
        else:
            colors["primary_variant"] = lighten(accent, 0.40)
            colors["user_bubble"] = darken(accent, 0.15)

    return {
        "colors": colors,
        "typography": TYPOGRAPHY,
        "spacing": SPACE,
        "radius": RADIUS,
        "window": WINDOW,
        "mode": mode,
    }


# Default (dark) for module-level imports
t = get_theme("dark")
