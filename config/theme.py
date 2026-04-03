"""
Design Foundation — Bảng màu, font, spacing, number format.

Centralized theme cho toàn bộ ứng dụng.
Hỗ trợ Dark/Light mode.
"""

# ═══════════════════════════════════════════════════════
# COLOR PALETTE
# ═══════════════════════════════════════════════════════

COLORS = {
    "dark": {
        "bg_primary":     "#1a1b2e",
        "bg_secondary":   "#232442",
        "bg_tertiary":    "#2d2f54",
        "accent":         "#6c63ff",
        "accent_hover":   "#5a52e0",
        "accent_light":   "#8b85ff",
        "success":        "#4ade80",
        "warning":        "#fbbf24",
        "error":          "#f87171",
        "text_primary":   "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_muted":     "#64748b",
        "border":         "#334155",
        "table_header":   "#1e293b",
        "table_stripe":   "#1e1f38",
        "table_selected": "#3b3d6e",
        "scrollbar":      "#475569",
        "input_bg":       "#2d2f54",
    },
    "light": {
        "bg_primary":     "#f8fafc",
        "bg_secondary":   "#ffffff",
        "bg_tertiary":    "#f1f5f9",
        "accent":         "#6c63ff",
        "accent_hover":   "#5a52e0",
        "accent_light":   "#ede9fe",
        "success":        "#22c55e",
        "warning":        "#f59e0b",
        "error":          "#ef4444",
        "text_primary":   "#0f172a",
        "text_secondary": "#475569",
        "text_muted":     "#94a3b8",
        "border":         "#e2e8f0",
        "table_header":   "#f1f5f9",
        "table_stripe":   "#f8fafc",
        "table_selected": "#ede9fe",
        "scrollbar":      "#cbd5e1",
        "input_bg":       "#ffffff",
    },
}

# ═══════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════

FONTS = {
    "family":      "Inter",
    "fallback":    "Segoe UI",
    "heading_lg":  ("Inter", 20, "bold"),
    "heading_md":  ("Inter", 16, "bold"),
    "heading_sm":  ("Inter", 14, "bold"),
    "body":        ("Inter", 13),
    "body_bold":   ("Inter", 13, "bold"),
    "caption":     ("Inter", 11),
    "mono":        ("Consolas", 12),
    "mono_sm":     ("Consolas", 11),
    "button":      ("Inter", 13, "bold"),
}

# ═══════════════════════════════════════════════════════
# SPACING & RADIUS
# ═══════════════════════════════════════════════════════

SPACING = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "xxl": 48}
RADIUS = {"sm": 4, "md": 8, "lg": 12}

# ═══════════════════════════════════════════════════════
# NUMBER FORMATS
# ═══════════════════════════════════════════════════════

NUMBER_FORMATS = {
    "text":     None,
    "number":   "#,##0",
    "currency": "#,##0",
    "date":     "DD/MM/YYYY",
}

# ═══════════════════════════════════════════════════════
# ICONS (text-based, no image dependency)
# ═══════════════════════════════════════════════════════

ICONS = {
    "login":     "\U0001F511",  # 🔑
    "logout":    "\U0001F6AA",  # 🚪
    "download":  "\U0001F4E5",  # 📥
    "import":    "\U0001F4C2",  # 📂
    "export":    "\U0001F4E4",  # 📤
    "settings":  "\u2699",      # ⚙
    "columns":   "\u2630",      # ☰
    "search":    "\U0001F50D",  # 🔍
    "refresh":   "\u21BB",      # ↻
    "success":   "\u2705",      # ✅
    "warning":   "\u26A0",      # ⚠
    "error":     "\u274C",      # ❌
    "info":      "\u2139",      # ℹ
    "filter":    "\U0001F50D",  # 🔍
    "detail":    "\U0001F4CB",  # 📋
    "xml":       "\U0001F4C4",  # 📄
}

# ═══════════════════════════════════════════════════════
# THEME HELPER
# ═══════════════════════════════════════════════════════

_current_mode = "light"


def get_colors(mode: str = None) -> dict:
    """Lấy color palette theo mode."""
    return COLORS.get(mode or _current_mode, COLORS["dark"])


def set_mode(mode: str):
    """Đổi theme mode."""
    global _current_mode
    if mode in COLORS:
        _current_mode = mode


def get_mode() -> str:
    return _current_mode


def format_number(value, fmt_type: str = "text") -> str:
    """Format số theo kiểu #,##0 cho hiển thị trong bảng."""
    if fmt_type not in ("number", "currency"):
        return str(value) if value else ""

    try:
        num = float(str(value).replace(",", ""))
        if num == int(num):
            return f"{int(num):,}".replace(",", ".")
        return f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value) if value else ""
