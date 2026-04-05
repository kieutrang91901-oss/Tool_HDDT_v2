"""
DataTable — Wrapper cho tksheet với theme + number format.

Component chính hiển thị bảng dữ liệu Excel-like.
Hỗ trợ:
- Virtual scrolling (10K+ dòng)
- Column config (ẩn/hiện, resize, reorder)
- Number format tự động (#,##0 cho cột tiền/SL)
- Context menu
- Multi-select
"""
import tkinter as tk
import tksheet
from typing import List, Optional, Callable, Dict, Any
from config.theme import get_colors, format_number, FONTS
from config.logger import get_logger

logger = get_logger(__name__)


class DataTable(tk.Frame):
    """Bảng dữ liệu Excel-like dựa trên tksheet."""

    def __init__(
        self,
        parent,
        columns: List[Dict] = None,
        on_select: Callable = None,
        on_double_click: Callable = None,
        on_right_click: Callable = None,
        height: int = 400,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.colors = get_colors()
        self._columns = columns or []
        self._on_select = on_select
        self._on_double_click = on_double_click
        self._on_right_click = on_right_click
        self._raw_data = []  # Dữ liệu gốc (chưa format)

        self.configure(bg=self.colors["bg_primary"])

        # Ensure fonts have 3 elements (family, size, style) — tksheet requires this
        body_font = FONTS.get("body", ("Segoe UI", 13))
        if len(body_font) < 3:
            body_font = (*body_font, "normal")
        header_font = FONTS.get("body_bold", ("Segoe UI", 13, "bold"))
        if len(header_font) < 3:
            header_font = (*header_font, "bold")

        # Tạo tksheet
        self.sheet = tksheet.Sheet(
            self,
            height=height,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            font=body_font,
            header_font=header_font,
        )
        self.sheet.pack(fill="both", expand=True)

        # Apply theme
        self._apply_theme()

        # Headers
        if self._columns:
            self._setup_headers()

        # Bindings
        self.sheet.enable_bindings(
            "single_select",
            "row_select",
            "column_select",
            "drag_select",
            "column_width_resize",
            "arrowkeys",
            "copy",
            "ctrl_select",
        )

        if on_select:
            self.sheet.extra_bindings("cell_select", self._handle_select)
            self.sheet.extra_bindings("row_select", self._handle_select)
        if on_double_click:
            # Sửa lỗi: bind vào doubleclick thay vì row_select để tránh việc click cái ăn luôn
            self.sheet.bind("<Double-Button-1>", self._handle_double_click)
        if on_right_click:
            self.sheet.extra_bindings("right_click_popup_menu", self._handle_right_click)

    # ═══════════════════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════════════════

    def _apply_theme(self):
        """Áp dụng theme lên tksheet."""
        c = self.colors
        self.sheet.set_options(
            # Header
            top_left_bg=c["table_header"],
            top_left_fg=c["text_secondary"],
            header_bg=c["table_header"],
            header_fg=c["text_primary"],
            header_border_fg=c["border"],
            header_selected_cells_bg=c["accent"],
            header_selected_cells_fg=c["text_primary"],
            # Index
            index_bg=c["table_header"],
            index_fg=c["text_secondary"],
            index_border_fg=c["border"],
            # Body
            table_bg=c["bg_secondary"],
            table_fg=c["text_primary"],
            table_border_fg=c["border"],
            table_selected_cells_border_fg=c["accent"],
            table_selected_cells_bg=c["table_selected"],
            table_selected_cells_fg=c["text_primary"],
            # Scrollbar
            # Frames
            frame_bg=c["bg_primary"],
            outline_thickness=0,
            outline_color=c["border"],
        )

    def refresh_theme(self):
        """Cập nhật theme (gọi khi user đổi dark/light)."""
        self.colors = get_colors()
        self.configure(bg=self.colors["bg_primary"])
        self._apply_theme()
        self.sheet.redraw()

    # ═══════════════════════════════════════════════════════
    # HEADERS
    # ═══════════════════════════════════════════════════════

    def _setup_headers(self):
        """Thiết lập headers từ column config."""
        headers = [c.get("name", c.get("key", "")) for c in self._columns]
        widths = [c.get("width", 120) for c in self._columns]

        self.sheet.headers(headers)
        for i, w in enumerate(widths):
            self.sheet.column_width(column=i, width=w)

    def set_columns(self, columns: List[Dict]):
        """Cập nhật danh sách cột (gọi khi user thay đổi column config)."""
        self._columns = columns
        self._setup_headers()
        # Re-render data nếu có
        if self._raw_data:
            self.set_data(self._raw_data)

    # ═══════════════════════════════════════════════════════
    # DATA
    # ═══════════════════════════════════════════════════════

    def set_data(self, data: List[List[Any]]):
        """Đặt dữ liệu cho bảng.

        data: List[List[Any]] — mỗi row là list giá trị theo thứ tự cột.
        Tự động format #,##0 cho cột currency/number.
        """
        self._raw_data = data

        # Format data theo column config
        formatted = []
        for row in data:
            f_row = []
            for i, val in enumerate(row):
                if i < len(self._columns):
                    fmt = self._columns[i].get("format", "text")
                    f_row.append(format_number(val, fmt))
                else:
                    f_row.append(str(val) if val else "")
            formatted.append(f_row)

        self.sheet.set_sheet_data(formatted)

        # Auto-fit column widths based on header + first row
        self._auto_fit_columns(formatted)

        # Alignment: right cho cột số
        try:
            for i, col in enumerate(self._columns):
                if col.get("format") in ("currency", "number"):
                    try:
                        self.sheet.align(columns=[i], align="e")
                    except TypeError:
                        try:
                            self.sheet.align("e", column=i)
                        except Exception:
                            pass
                elif col.get("format") == "date":
                    try:
                        self.sheet.align(columns=[i], align="center")
                    except TypeError:
                        try:
                            self.sheet.align("center", column=i)
                        except Exception:
                            pass
        except Exception:
            pass  # Skip alignment if tksheet API incompatible

        self.sheet.redraw()

    def _auto_fit_columns(self, formatted_data: list):
        """Tự động căn chỉnh độ rộng cột theo nội dung header + dòng đầu tiên."""
        if not self._columns:
            return

        CHAR_WIDTH = 9   # Approximate pixel per character
        MIN_WIDTH = 50
        MAX_WIDTH = 400
        PADDING = 24      # Padding cho border + margin

        for i, col in enumerate(self._columns):
            # Width from header text
            header_text = col.get("name", col.get("key", ""))
            header_w = len(str(header_text)) * CHAR_WIDTH + PADDING

            # Width from first row data
            data_w = MIN_WIDTH
            if formatted_data and i < len(formatted_data[0]):
                cell_text = str(formatted_data[0][i])
                data_w = len(cell_text) * CHAR_WIDTH + PADDING

            # Use the wider of header or data, clamped
            final_w = max(MIN_WIDTH, min(MAX_WIDTH, max(header_w, data_w)))
            self.sheet.column_width(column=i, width=final_w)

    def get_data(self) -> List[List[Any]]:
        """Lấy dữ liệu gốc (chưa format)."""
        return self._raw_data

    def get_selected_rows(self) -> List[int]:
        """Lấy indices của các dòng đang chọn."""
        try:
            selected = self.sheet.get_currently_selected()
            if selected:
                return list(self.sheet.get_selected_rows())
            return []
        except Exception:
            return []

    def get_row_data(self, row_idx: int) -> List[Any]:
        """Lấy dữ liệu gốc 1 dòng."""
        if 0 <= row_idx < len(self._raw_data):
            return self._raw_data[row_idx]
        return []

    def clear(self):
        """Xóa toàn bộ dữ liệu."""
        self._raw_data = []
        self.sheet.set_sheet_data([])
        self.sheet.redraw()

    def get_row_count(self) -> int:
        return len(self._raw_data)

    # ═══════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════

    def _handle_select(self, event=None):
        if self._on_select:
            rows = self.get_selected_rows()
            if rows:
                self._on_select(rows[0])

    def _handle_double_click(self, event=None):
        if self._on_double_click:
            rows = self.get_selected_rows()
            if rows:
                self._on_double_click(rows[0])

    def _handle_right_click(self, event=None):
        if self._on_right_click:
            rows = self.get_selected_rows()
            if rows:
                self._on_right_click(rows[0], event)
