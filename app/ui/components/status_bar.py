"""
StatusBar — Thanh trạng thái phía dưới cửa sổ.

Hiển thị: Trạng thái kết nối, MST, số dòng, thông báo...
"""
import customtkinter as ctk
from config.theme import get_colors, FONTS


class StatusBar(ctk.CTkFrame):
    """Thanh trạng thái dưới cùng."""

    def __init__(self, parent, **kwargs):
        colors = get_colors()
        super().__init__(
            parent,
            fg_color=colors["bg_secondary"],
            corner_radius=0,
            height=28,
            **kwargs,
        )
        self.pack_propagate(False)
        self.colors = colors

        # Left: Connection status
        self._status_label = ctk.CTkLabel(
            self,
            text="Chưa đăng nhập",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=colors["text_muted"],
        )
        self._status_label.pack(side="left", padx=12)

        # Center: Message
        self._msg_label = ctk.CTkLabel(
            self,
            text="",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=colors["text_secondary"],
        )
        self._msg_label.pack(side="left", padx=12, fill="x", expand=True)

        # Right: Row count
        self._count_label = ctk.CTkLabel(
            self,
            text="",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=colors["text_muted"],
        )
        self._count_label.pack(side="right", padx=12)

        # Right: Version
        from config.settings import APP_VERSION
        self._version_label = ctk.CTkLabel(
            self,
            text=f"v{APP_VERSION}",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=colors["text_muted"],
        )
        self._version_label.pack(side="right", padx=8)

    def set_status(self, text: str, connected: bool = False):
        color = self.colors["success"] if connected else self.colors["text_muted"]
        icon = "● " if connected else "○ "
        self._status_label.configure(text=f"{icon}{text}", text_color=color)

    def set_message(self, text: str):
        self._msg_label.configure(text=text)

    def set_count(self, count: int, label: str = "dòng"):
        self._count_label.configure(text=f"{count:,} {label}" if count > 0 else "")

    def clear_message(self):
        self._msg_label.configure(text="")
