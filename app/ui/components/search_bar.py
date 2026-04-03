"""
SearchBar — Ô tìm kiếm + bộ lọc nhanh.
DatePicker — Chọn từ ngày / đến ngày.

Gộp chung vì được dùng cùng nhau trên toolbar Invoice List.
"""
import customtkinter as ctk
from datetime import datetime, timedelta
from config.theme import get_colors, FONTS


class SearchBar(ctk.CTkFrame):
    """Ô tìm kiếm text."""

    def __init__(self, parent, placeholder: str = "Tìm kiếm...", on_search=None, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._on_search = on_search

        self._entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=colors["input_bg"],
            border_color=colors["border"],
            text_color=colors["text_primary"],
            placeholder_text_color=colors["text_muted"],
            width=250,
            height=32,
            corner_radius=6,
        )
        self._entry.pack(side="left", padx=(0, 4))
        self._entry.bind("<Return>", self._do_search)

        # Search button
        ctk.CTkButton(
            self, text="Tìm", width=50, height=32,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=colors["accent"],
            hover_color=colors["accent_hover"],
            corner_radius=6,
            command=self._do_search,
        ).pack(side="left")

    def _do_search(self, event=None):
        if self._on_search:
            self._on_search(self._entry.get().strip())

    def get_text(self) -> str:
        return self._entry.get().strip()

    def clear(self):
        self._entry.delete(0, "end")


class DatePicker(ctk.CTkFrame):
    """Chọn khoảng ngày (từ ngày — đến ngày)."""

    def __init__(self, parent, on_change=None, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._on_change = on_change
        label_font = FONTS.get("caption", ("Segoe UI", 11))
        entry_font = FONTS.get("body", ("Segoe UI", 13))

        # Từ ngày
        ctk.CTkLabel(self, text="Từ:", font=label_font, text_color=colors["text_secondary"]).pack(side="left", padx=(0, 4))
        self._from_entry = ctk.CTkEntry(
            self, width=110, height=32, font=entry_font,
            fg_color=colors["input_bg"], border_color=colors["border"],
            text_color=colors["text_primary"],
            placeholder_text="DD/MM/YYYY",
            placeholder_text_color=colors["text_muted"],
        )
        self._from_entry.pack(side="left", padx=(0, 8))

        # Đến ngày
        ctk.CTkLabel(self, text="Đến:", font=label_font, text_color=colors["text_secondary"]).pack(side="left", padx=(0, 4))
        self._to_entry = ctk.CTkEntry(
            self, width=110, height=32, font=entry_font,
            fg_color=colors["input_bg"], border_color=colors["border"],
            text_color=colors["text_primary"],
            placeholder_text="DD/MM/YYYY",
            placeholder_text_color=colors["text_muted"],
        )
        self._to_entry.pack(side="left", padx=(0, 8))

        # Quick buttons
        for text, days in [("7 ngày", 7), ("30 ngày", 30), ("90 ngày", 90)]:
            ctk.CTkButton(
                self, text=text, width=55, height=28,
                font=FONTS.get("caption", ("Segoe UI", 11)),
                fg_color=colors["bg_tertiary"],
                hover_color=colors["border"],
                text_color=colors["text_secondary"],
                corner_radius=4,
                command=lambda d=days: self._set_quick_range(d),
            ).pack(side="left", padx=2)

        # Default: 30 ngày
        self._set_quick_range(30)

    def _set_quick_range(self, days: int):
        today = datetime.now()
        from_date = today - timedelta(days=days)

        self._from_entry.delete(0, "end")
        self._from_entry.insert(0, from_date.strftime("%d/%m/%Y"))

        self._to_entry.delete(0, "end")
        self._to_entry.insert(0, today.strftime("%d/%m/%Y"))

        if self._on_change:
            self._on_change(self.get_from(), self.get_to())

    def get_from(self) -> str:
        """Lấy từ ngày (format DD/MM/YYYY)."""
        return self._from_entry.get().strip()

    def get_to(self) -> str:
        """Lấy đến ngày (format DD/MM/YYYY)."""
        return self._to_entry.get().strip()

    def get_api_format(self):
        """Lấy cặp ngày format cho API: DD/MM/YYYYT00:00:00"""
        f = self.get_from()
        t = self.get_to()
        return f"{f}T00:00:00" if f else "", f"{t}T23:59:59" if t else ""
