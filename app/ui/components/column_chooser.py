"""
ColumnChooser — Dialog cho user chọn cột hiển thị.

Hỗ trợ:
- Checkbox ẩn/hiện từng cột
- Tìm kiếm cột nhanh (search)
- Kéo lên/xuống thay đổi thứ tự
- Hiển thị cả cột Tầng 1 (fixed) và Tầng 2 (dynamic extras)
- Reset về mặc định
"""
import customtkinter as ctk
from typing import List, Callable, Optional
from config.theme import get_colors, FONTS
from app.models.entities import ColumnConfig


class ColumnChooser(ctk.CTkToplevel):
    """Dialog chọn cột hiển thị."""

    def __init__(
        self,
        parent,
        columns: List[ColumnConfig],
        on_apply: Callable[[List[ColumnConfig]], None] = None,
        on_reset: Callable = None,
        title: str = "Cấu hình cột hiển thị",
    ):
        super().__init__(parent)
        self.colors = get_colors()
        self._columns = [self._clone_col(c) for c in columns]  # Deep copy
        self._on_apply = on_apply
        self._on_reset = on_reset
        self._checkboxes = []
        self._vars = []
        self._row_widgets = []  # Track row widgets for search filter
        self._search_text = ""

        # Window
        self.title(title)
        self.geometry("450x600")
        self.configure(fg_color=self.colors["bg_primary"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.resizable(False, True)

        self._build_ui()
        self._center()

    def _build_ui(self):
        c = self.colors

        # Header
        header = ctk.CTkFrame(self, fg_color=c["bg_secondary"], height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="Cau hinh cot hien thi",
            font=FONTS.get("heading_sm", ("Segoe UI", 14, "bold")),
            text_color=c["text_primary"],
        ).pack(side="left", padx=16)

        # ── Search bar ───────────────────────────────
        search_frame = ctk.CTkFrame(self, fg_color=c["bg_secondary"], corner_radius=0)
        search_frame.pack(fill="x", padx=0, pady=(0, 4))

        self._search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Tim kiem cot...",
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            text_color=c["text_primary"],
            placeholder_text_color=c["text_muted"],
            height=32,
        )
        self._search_entry.pack(fill="x", padx=12, pady=8)
        self._search_entry.bind("<KeyRelease>", self._on_search)

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=c["bg_primary"],
            scrollbar_button_color=c["scrollbar"],
        )
        self._scroll.pack(fill="both", expand=True, padx=8, pady=4)

        for i, col in enumerate(self._columns):
            self._add_column_row(i, col)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color=c["bg_secondary"], height=56, corner_radius=0)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)

        # Move up/down
        ctk.CTkButton(
            btn_frame, text="Len", width=70, height=32,
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_primary"],
            font=FONTS.get("body", ("Segoe UI", 13)),
            command=self._move_up,
        ).pack(side="left", padx=(12, 4), pady=12)

        ctk.CTkButton(
            btn_frame, text="Xuong", width=70, height=32,
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_primary"],
            font=FONTS.get("body", ("Segoe UI", 13)),
            command=self._move_down,
        ).pack(side="left", padx=4, pady=12)

        # Reset
        if self._on_reset:
            ctk.CTkButton(
                btn_frame, text="Reset", width=70, height=32,
                fg_color=c["warning"], hover_color="#d97706",
                text_color="#1a1a1a",
                font=FONTS.get("body", ("Segoe UI", 13)),
                command=self._reset,
            ).pack(side="left", padx=4, pady=12)

        # Cancel / Apply
        ctk.CTkButton(
            btn_frame, text="Huy", width=70, height=32,
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_primary"],
            font=FONTS.get("body", ("Segoe UI", 13)),
            command=self.destroy,
        ).pack(side="right", padx=(4, 12), pady=12)

        ctk.CTkButton(
            btn_frame, text="Ap dung", width=90, height=32,
            fg_color=c["accent"], hover_color=c["accent_hover"],
            font=FONTS.get("body", ("Segoe UI", 13)),
            command=self._apply,
        ).pack(side="right", padx=4, pady=12)

    def _add_column_row(self, idx: int, col: ColumnConfig):
        c = self.colors

        row = ctk.CTkFrame(self._scroll, fg_color="transparent", height=36)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # Checkbox
        var = ctk.BooleanVar(value=col.is_visible)
        cb = ctk.CTkCheckBox(
            row, text="",
            variable=var,
            width=24,
            fg_color=c["accent"],
            hover_color=c["accent_hover"],
            border_color=c["border"],
            checkmark_color="#ffffff",
        )
        cb.pack(side="left", padx=(8, 4))

        # Name
        name_text = col.display_name
        if col.is_dynamic:
            name_text += f"  [D:{col.scope}]"

        ctk.CTkLabel(
            row, text=name_text,
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=c["text_primary"],
            anchor="w",
        ).pack(side="left", padx=4, fill="x", expand=True)

        # Format badge
        if col.format_type in ("currency", "number"):
            ctk.CTkLabel(
                row, text="#,##0",
                font=FONTS.get("mono_sm", ("Consolas", 10)),
                text_color=c["accent_light"],
                width=50,
            ).pack(side="right", padx=8)

        self._vars.append(var)
        self._checkboxes.append(cb)
        self._row_widgets.append(row)

        # Selection binding (highlight row)
        row.bind("<Button-1>", lambda e, i=idx: self._select_row(i))

    # ═══════════════════════════════════════════════════════
    # SEARCH FILTER
    # ═══════════════════════════════════════════════════════

    def _on_search(self, event=None):
        """Lọc danh sách cột theo từ khóa tìm kiếm."""
        text = self._search_entry.get().strip().lower()
        self._search_text = text

        for i, col in enumerate(self._columns):
            if i < len(self._row_widgets):
                widget = self._row_widgets[i]
                name = col.display_name.lower()
                scope = (col.scope or "").lower()
                key = col.column_key.lower()

                if not text or text in name or text in scope or text in key:
                    widget.pack(fill="x", pady=1)
                else:
                    widget.pack_forget()

    _selected_idx = -1

    def _select_row(self, idx: int):
        c = self.colors
        # Unhighlight previous
        if 0 <= self._selected_idx < len(self._row_widgets):
            self._row_widgets[self._selected_idx].configure(fg_color="transparent")
        # Highlight new
        self._selected_idx = idx
        if 0 <= idx < len(self._row_widgets):
            self._row_widgets[idx].configure(fg_color=c["table_selected"])

    def _move_up(self):
        idx = self._selected_idx
        if idx > 0:
            self._columns[idx], self._columns[idx - 1] = self._columns[idx - 1], self._columns[idx]
            self._selected_idx = idx - 1
            self._rebuild_list()

    def _move_down(self):
        idx = self._selected_idx
        if 0 <= idx < len(self._columns) - 1:
            self._columns[idx], self._columns[idx + 1] = self._columns[idx + 1], self._columns[idx]
            self._selected_idx = idx + 1
            self._rebuild_list()

    def _rebuild_list(self):
        # Sync visibility from current vars
        for i, var in enumerate(self._vars):
            if i < len(self._columns):
                self._columns[i].is_visible = var.get()

        # Clear and rebuild
        for w in self._scroll.winfo_children():
            w.destroy()
        self._checkboxes.clear()
        self._vars.clear()
        self._row_widgets.clear()
        for i, col in enumerate(self._columns):
            self._add_column_row(i, col)
        # Re-apply search filter
        if self._search_text:
            self._on_search()
        # Re-highlight selected
        if 0 <= self._selected_idx < len(self._row_widgets):
            self._row_widgets[self._selected_idx].configure(fg_color=self.colors["table_selected"])

    def _apply(self):
        # Sync final state
        for i, var in enumerate(self._vars):
            if i < len(self._columns):
                self._columns[i].is_visible = var.get()
                self._columns[i].sort_order = i

        if self._on_apply:
            self._on_apply(self._columns)
        self.destroy()

    def _reset(self):
        if self._on_reset:
            self._on_reset()
        self.destroy()

    def _center(self):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{x}+{y}")

    @staticmethod
    def _clone_col(c: ColumnConfig) -> ColumnConfig:
        return ColumnConfig(
            column_key=c.column_key, display_name=c.display_name,
            table_name=c.table_name, is_visible=c.is_visible,
            sort_order=c.sort_order, width=c.width,
            format_type=c.format_type, is_dynamic=c.is_dynamic,
            scope=c.scope,
        )
