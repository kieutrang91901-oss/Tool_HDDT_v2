"""
LoadingIndicator — Spinner / Progress bar.

Hiển thị khi đang tải dữ liệu, parse XML, download...
"""
import customtkinter as ctk
from config.theme import get_colors, FONTS


class LoadingIndicator(ctk.CTkFrame):
    """Loading overlay với progress bar + message."""

    def __init__(self, parent, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color=colors["bg_primary"], **kwargs)
        self.colors = colors

        # Message
        self._msg = ctk.CTkLabel(
            self,
            text="Đang xử lý...",
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=colors["text_secondary"],
        )
        self._msg.pack(pady=(0, 8))

        # Progress bar
        self._progress = ctk.CTkProgressBar(
            self,
            width=300,
            height=6,
            progress_color=colors["accent"],
            fg_color=colors["bg_tertiary"],
        )
        self._progress.pack(pady=4)
        self._progress.set(0)

        # Percentage
        self._pct = ctk.CTkLabel(
            self,
            text="0%",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=colors["text_muted"],
        )
        self._pct.pack(pady=(4, 0))

    def set_progress(self, current: int, total: int, message: str = ""):
        """Cập nhật progress."""
        if total > 0:
            pct = current / total
            self._progress.set(pct)
            self._pct.configure(text=f"{current}/{total} ({pct:.0%})")
        if message:
            self._msg.configure(text=message)

    def set_indeterminate(self, message: str = "Đang xử lý..."):
        """Chuyển sang mode quay vòng (không biết tổng)."""
        self._msg.configure(text=message)
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._pct.configure(text="")

    def stop(self):
        self._progress.stop()
        self._progress.configure(mode="determinate")

    def reset(self):
        self.stop()
        self._progress.set(0)
        self._pct.configure(text="")
        self._msg.configure(text="")
