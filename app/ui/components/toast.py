"""
Toast — Thông báo popup cho success/error/warning/info.

Hiển thị tạm thời ở góc phải dưới, tự biến mất sau N giây.
"""
import customtkinter as ctk
from config.theme import get_colors, FONTS, SPACING


class Toast(ctk.CTkToplevel):
    """Popup thông báo tự mất."""

    TYPES = {
        "success": {"icon": "✓", "color_key": "success"},
        "error":   {"icon": "✕", "color_key": "error"},
        "warning": {"icon": "⚠", "color_key": "warning"},
        "info":    {"icon": "ℹ", "color_key": "accent"},
    }

    def __init__(
        self,
        parent,
        message: str,
        toast_type: str = "info",
        duration: int = 3000,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.colors = get_colors()
        cfg = self.TYPES.get(toast_type, self.TYPES["info"])

        # Window config
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=self.colors["bg_secondary"])

        # Frame
        frame = ctk.CTkFrame(
            self,
            fg_color=self.colors["bg_secondary"],
            border_color=self.colors[cfg["color_key"]],
            border_width=2,
            corner_radius=8,
        )
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Icon
        icon_label = ctk.CTkLabel(
            frame,
            text=cfg["icon"],
            font=("Segoe UI", 18),
            text_color=self.colors[cfg["color_key"]],
            width=30,
        )
        icon_label.pack(side="left", padx=(12, 4), pady=10)

        # Message
        msg_label = ctk.CTkLabel(
            frame,
            text=message,
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=self.colors["text_primary"],
            wraplength=350,
            justify="left",
        )
        msg_label.pack(side="left", padx=(4, 16), pady=10, fill="x", expand=True)

        # Position: center of parent window
        self.update_idletasks()
        parent_root = parent.winfo_toplevel()
        
        # Lấy kích thước và vị trí của cửa sổ cha
        p_width = parent_root.winfo_width()
        p_height = parent_root.winfo_height()
        p_x = parent_root.winfo_x()
        p_y = parent_root.winfo_y()
        
        # Nếu cha chưa hiện hoặc quá nhỏ, lấy kích thước màn hình
        if p_width < 100 or p_height < 100:
            p_width = self.winfo_screenwidth()
            p_height = self.winfo_screenheight()
            p_x = 0
            p_y = 0

        # Căn giữa hiển thị Toast
        x = p_x + (p_width - self.winfo_width()) // 2
        y = p_y + (p_height - self.winfo_height()) // 2
        
        # Dịch lên một chút so với tâm chính xác cho đẹp hơn (~10%)
        y = int(y - p_height * 0.1)
        
        self.geometry(f"+{x}+{y}")

        # Auto-hide
        self.after(duration, self._fade_out)

    def _fade_out(self):
        try:
            self.destroy()
        except Exception:
            pass


def show_toast(parent, message: str, toast_type: str = "info", duration: int = 3000):
    """Helper function để hiển thị toast."""
    Toast(parent, message, toast_type, duration)
