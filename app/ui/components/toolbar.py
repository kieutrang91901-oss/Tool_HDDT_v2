"""
Toolbar — Thanh công cụ phía trên bảng dữ liệu.

Tự động co giãn: luôn hiển thị tất cả nút bất kể kích thước cửa sổ.
"""
import customtkinter as ctk
from config.theme import get_colors, FONTS, SPACING


class ToolbarButton(ctk.CTkButton):
    """Nút trên toolbar với icon + text."""

    def __init__(self, parent, text: str, icon: str = "", command=None, style="default", **kwargs):
        colors = get_colors()

        if style == "primary":
            fg = colors["accent"]
            hover = colors["accent_hover"]
            text_c = "#ffffff"
        elif style == "danger":
            fg = colors["error"]
            hover = "#dc2626"
            text_c = "#ffffff"
        else:
            fg = colors["bg_tertiary"]
            hover = colors["border"]
            text_c = colors["text_primary"]

        display = f"{icon} {text}" if icon else text

        super().__init__(
            parent,
            text=display,
            command=command,
            fg_color=fg,
            hover_color=hover,
            text_color=text_c,
            font=FONTS.get("body", ("Segoe UI", 13)),
            corner_radius=6,
            height=32,
            **kwargs,
        )


class Toolbar(ctk.CTkFrame):
    """Thanh công cụ tái sử dụng — tự động wrap khi cửa sổ nhỏ."""

    def __init__(self, parent, **kwargs):
        colors = get_colors()
        super().__init__(
            parent,
            fg_color=colors["bg_secondary"],
            corner_radius=0,
            **kwargs,
        )
        # Cho phép co giãn theo nội dung thay vì cố định height
        self._buttons = {}
        self._items = []  # List of (widget, type) for layout

        # Inner frame chứa tất cả button (dùng grid để wrap)
        self._inner = ctk.CTkFrame(self, fg_color="transparent")
        self._inner.pack(fill="x", padx=4, pady=6)

        self._col = 0

    def add_button(
        self,
        key: str,
        text: str,
        icon: str = "",
        command=None,
        style: str = "default",
        side: str = "left",
    ) -> ToolbarButton:
        """Thêm nút vào toolbar."""
        btn = ToolbarButton(self._inner, text=text, icon=icon, command=command, style=style)
        btn.pack(side=side, padx=2, pady=2)
        self._buttons[key] = btn
        return btn

    def add_separator(self):
        """Thêm đường phân cách."""
        colors = get_colors()
        sep = ctk.CTkFrame(self._inner, width=1, fg_color=colors["border"], height=24)
        sep.pack(side="left", padx=6, pady=4)

    def get_button(self, key: str):
        return self._buttons.get(key)

    def set_button_state(self, key: str, enabled: bool):
        btn = self._buttons.get(key)
        if btn:
            btn.configure(state="normal" if enabled else "disabled")
