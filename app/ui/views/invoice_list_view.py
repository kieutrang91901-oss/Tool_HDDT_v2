"""
InvoiceListView — Màn hình chính: Bảng danh sách HĐ + toolbar.

Tích hợp: Import offline, Download từ API, Export Excel, Column Config.
"""
import customtkinter as ctk
import threading
import os
from tkinter import filedialog
from typing import List

from config.theme import get_colors, FONTS
from config.column_config import SUMMARY_COLUMNS_DEFAULT
from config.logger import get_logger
from app.models.entities import InvoiceData, ColumnConfig
from app.ui.components.toolbar import Toolbar
from app.ui.components.data_table import DataTable
from app.ui.components.search_bar import SearchBar, DatePicker
from app.ui.components.loading_indicator import LoadingIndicator
from app.ui.components.column_chooser import ColumnChooser
from app.ui.components.toast import show_toast

logger = get_logger(__name__)


class InvoiceListView(ctk.CTkFrame):
    """Bảng danh sách hóa đơn — Màn hình chính."""

    def __init__(self, parent, main_window, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color=colors["bg_primary"], **kwargs)
        self.main = main_window
        self.colors = colors
        self._invoices: List[InvoiceData] = []
        self._columns: List[dict] = []

        self._init_columns()
        self._build_ui()

    def _init_columns(self):
        """Load cột từ DB hoặc dùng mặc định."""
        stored = self.main.db.get_columns("summary", visible_only=False)
        if stored:
            self._columns = [
                {"key": c.column_key, "name": c.display_name,
                 "format": c.format_type, "width": c.width,
                 "visible": c.is_visible, "is_dynamic": c.is_dynamic, "scope": c.scope}
                for c in stored
            ]
        else:
            self._columns = [dict(c) for c in SUMMARY_COLUMNS_DEFAULT]
            # Save defaults to DB
            for i, c in enumerate(self._columns):
                self.main.db.upsert_column(ColumnConfig(
                    column_key=c["key"], display_name=c["name"],
                    table_name="summary", is_visible=c["visible"],
                    sort_order=i, width=c["width"], format_type=c["format"],
                ))

    def _get_visible_columns(self) -> List[dict]:
        return [c for c in self._columns if c.get("visible", True)]

    def _build_ui(self):
        c = self.colors

        # ── Toolbar ──────────────────────────────────
        self._toolbar = Toolbar(self)
        self._toolbar.pack(fill="x")

        self._toolbar.add_button("import", "Import", icon="📂", command=self._import_files, style="default")
        self._toolbar.add_button("download", "Tải HĐ", icon="📥", command=self._download_invoices, style="primary")
        self._toolbar.add_separator()
        self._toolbar.add_button("export_summary", "Export TH", icon="📤", command=self._export_summary)
        self._toolbar.add_button("export_detail", "Export CT", icon="📤", command=self._export_detail)
        self._toolbar.add_separator()
        self._toolbar.add_button("columns", "Cột", icon="☰", command=self._open_column_chooser)
        self._toolbar.add_button("clear", "Xóa", command=self._clear_data)

        # ── Filter bar ───────────────────────────────
        filter_frame = ctk.CTkFrame(self, fg_color=c["bg_secondary"], height=44, corner_radius=0)
        filter_frame.pack(fill="x")
        filter_frame.pack_propagate(False)

        # Search
        self._search = SearchBar(filter_frame, on_search=self._do_search)
        self._search.pack(side="left", padx=8, pady=6)

        # DatePicker
        self._date_picker = DatePicker(filter_frame)
        self._date_picker.pack(side="left", padx=8, pady=6)

        # Type filter
        self._type_var = ctk.StringVar(value="Tất cả")
        ctk.CTkSegmentedButton(
            filter_frame, values=["Tất cả", "Mua vào", "Bán ra"],
            variable=self._type_var, font=FONTS.get("caption", ("Segoe UI", 11)),
            selected_color=c["accent"], selected_hover_color=c["accent_hover"],
            unselected_color=c["bg_tertiary"], unselected_hover_color=c["border"],
            text_color=c["text_primary"],
        ).pack(side="right", padx=8, pady=6)

        # ── Data Table ───────────────────────────────
        visible = self._get_visible_columns()
        self._table = DataTable(
            self, columns=visible,
            on_select=self._on_row_select,
            on_double_click=self._on_row_double_click,
        )
        self._table.pack(fill="both", expand=True, padx=4, pady=4)

        # ── Loading overlay (hidden) ─────────────────
        self._loading = LoadingIndicator(self)

    # ═══════════════════════════════════════════════════════
    # IMPORT OFFLINE
    # ═══════════════════════════════════════════════════════

    def _import_files(self):
        """Mở dialog chọn file XML/ZIP/Folder."""
        paths = filedialog.askopenfilenames(
            title="Chọn file XML / ZIP",
            filetypes=[
                ("Invoice files", "*.xml *.zip"),
                ("XML files", "*.xml"),
                ("ZIP files", "*.zip"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            # Try folder
            folder = filedialog.askdirectory(title="Hoặc chọn thư mục")
            if folder:
                paths = [folder]
            else:
                return

        self._show_loading("Đang đọc file...")

        def _parse_thread():
            invoices = self.main.parser_service.parse_input(
                list(paths),
                progress_callback=lambda cur, total: self.after(
                    0, lambda c=cur, t=total: self._loading.set_progress(c, t, f"Parse {c}/{t}")
                ),
            )
            self.after(0, lambda: self._on_parse_done(invoices))

        threading.Thread(target=_parse_thread, daemon=True).start()

    def _on_parse_done(self, invoices: List[InvoiceData]):
        self._hide_loading()
        self._invoices.extend(invoices)
        self._refresh_table()

        ok = sum(1 for i in invoices if not i.parse_error)
        err = len(invoices) - ok
        msg = f"Đã import {ok} HĐ"
        if err > 0:
            msg += f" ({err} lỗi)"
        show_toast(self.main, msg, "success" if err == 0 else "warning")

    # ═══════════════════════════════════════════════════════
    # DOWNLOAD FROM API
    # ═══════════════════════════════════════════════════════

    def _download_invoices(self):
        """Tra cứu + tải HĐ từ cổng thuế."""
        if not self.main.auth_service.is_logged_in:
            show_toast(self.main, "Vui lòng đăng nhập trước", "warning")
            return

        self._show_loading("Đang tra cứu...")

        loai_map = {"Tất cả": "", "Mua vào": "purchase", "Bán ra": "sold"}
        loai = loai_map.get(self._type_var.get(), "")
        tu, den = self._date_picker.get_api_format()

        def _query_thread():
            results = []
            for l in (["purchase", "sold"] if not loai else [loai]):
                qr = self.main.query_service.query_invoices(l, tu, den)
                if qr.success:
                    results.extend(qr.invoices)
                    self.main.query_service.cache_query_results(
                        self.main.auth_service.current_mst, qr.invoices
                    )
            self.after(0, lambda: self._on_query_done(results))

        threading.Thread(target=_query_thread, daemon=True).start()

    def _on_query_done(self, results):
        self._hide_loading()
        count = len(results)
        show_toast(self.main, f"Tìm thấy {count} hóa đơn", "success" if count > 0 else "info")
        self.main.status_bar.set_message(f"Đã tải {count} HĐ từ cổng thuế")

    # ═══════════════════════════════════════════════════════
    # EXPORT
    # ═══════════════════════════════════════════════════════

    def _export_summary(self):
        if not self._invoices:
            show_toast(self.main, "Không có dữ liệu để export", "warning")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="HDDT_TongHop.xlsx",
        )
        if not path:
            return

        cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                for c in self._get_visible_columns()]

        result = self.main.excel_service.export_summary(self._invoices, path, cols)
        if result["success"]:
            show_toast(self.main, f"Đã export {result['row_count']} dòng", "success")
            os.startfile(path)
        else:
            show_toast(self.main, f"Lỗi export: {result['error_msg']}", "error")

    def _export_detail(self):
        if not self._invoices:
            show_toast(self.main, "Không có dữ liệu để export", "warning")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="HDDT_ChiTiet.xlsx",
        )
        if not path:
            return

        from config.column_config import DETAIL_COLUMNS_DEFAULT
        s_cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                  for c in self._get_visible_columns()]
        d_cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                  for c in DETAIL_COLUMNS_DEFAULT if c["visible"]]

        result = self.main.excel_service.export_detail(self._invoices, path, s_cols, d_cols)
        if result["success"]:
            show_toast(self.main, f"Đã export {result['row_count']} dòng chi tiết", "success")
            os.startfile(path)
        else:
            show_toast(self.main, f"Lỗi export: {result['error_msg']}", "error")

    # ═══════════════════════════════════════════════════════
    # COLUMN CHOOSER
    # ═══════════════════════════════════════════════════════

    def _open_column_chooser(self):
        configs = [
            ColumnConfig(
                column_key=c["key"], display_name=c["name"],
                table_name="summary", is_visible=c.get("visible", True),
                sort_order=i, width=c.get("width", 120),
                format_type=c.get("format", "text"),
                is_dynamic=c.get("is_dynamic", False), scope=c.get("scope", ""),
            )
            for i, c in enumerate(self._columns)
        ]
        ColumnChooser(self, configs, on_apply=self._apply_columns, on_reset=self._reset_columns)

    def _apply_columns(self, configs: List[ColumnConfig]):
        self._columns = [
            {"key": c.column_key, "name": c.display_name, "format": c.format_type,
             "width": c.width, "visible": c.is_visible,
             "is_dynamic": c.is_dynamic, "scope": c.scope}
            for c in configs
        ]
        # Save to DB
        for i, c in enumerate(configs):
            c.sort_order = i
            c.table_name = "summary"
            self.main.db.upsert_column(c)

        self._table.set_columns(self._get_visible_columns())
        self._refresh_table()
        show_toast(self.main, "Cấu hình cột đã cập nhật", "success")

    def _reset_columns(self):
        self._columns = [dict(c) for c in SUMMARY_COLUMNS_DEFAULT]
        for i, c in enumerate(self._columns):
            self.main.db.upsert_column(ColumnConfig(
                column_key=c["key"], display_name=c["name"],
                table_name="summary", is_visible=c["visible"],
                sort_order=i, width=c["width"], format_type=c["format"],
            ))
        self._table.set_columns(self._get_visible_columns())
        self._refresh_table()
        show_toast(self.main, "Đã reset cột về mặc định", "info")

    # ═══════════════════════════════════════════════════════
    # TABLE DATA
    # ═══════════════════════════════════════════════════════

    def _refresh_table(self):
        """Refresh bảng dữ liệu."""
        visible = self._get_visible_columns()
        rows = []
        for idx, inv in enumerate(self._invoices, 1):
            row = []
            for col in visible:
                key = col["key"]
                row.append(self._get_inv_value(inv, key, idx))
            rows.append(row)

        self._table.set_data(rows)
        self.main.status_bar.set_count(len(rows))

    def _get_inv_value(self, inv: InvoiceData, key: str, idx: int):
        """Lấy giá trị 1 ô theo column key."""
        mapping = {
            "stt": idx,
            "ky_hieu": inv.ky_hieu,
            "so_hd": inv.so_hd,
            "ngay_lap": inv.ngay_lap,
            "mst_ban": inv.mst_ban,
            "ten_ban": inv.ten_ban,
            "mst_mua": inv.mst_mua,
            "ten_mua": inv.ten_mua,
            "tong_chua_thue": inv.tong_chua_thue,
            "tong_thue": inv.tong_thue,
            "tong_thanh_toan": inv.tong_thanh_toan_so,
            "trang_thai": inv.status_label,
            "vendor": inv.nha_cung_cap,
            "mccqt": inv.mccqt,
            "fkey": inv.fkey,
            "portal_link": inv.portal_link,
        }
        if key in mapping:
            return mapping[key]
        # Dynamic extras
        from config.column_config import parse_dynamic_column_key
        scope, fkey = parse_dynamic_column_key(key)
        extras_map = {"header": inv.extras_header, "seller": inv.extras_seller,
                      "buyer": inv.extras_buyer, "payment": inv.extras_payment,
                      "invoice": inv.extras_invoice}
        return extras_map.get(scope, {}).get(fkey, "")

    # ═══════════════════════════════════════════════════════
    # SEARCH / FILTER
    # ═══════════════════════════════════════════════════════

    def _do_search(self, text: str):
        # Simple in-memory filter
        if not text:
            self._refresh_table()
            return
        text_lower = text.lower()
        filtered = [
            inv for inv in self._invoices
            if text_lower in inv.ten_ban.lower()
            or text_lower in inv.mst_ban.lower()
            or text_lower in inv.so_hd.lower()
            or text_lower in inv.ky_hieu.lower()
        ]
        self._show_filtered(filtered)

    def _show_filtered(self, invoices):
        visible = self._get_visible_columns()
        rows = []
        for idx, inv in enumerate(invoices, 1):
            row = [self._get_inv_value(inv, c["key"], idx) for c in visible]
            rows.append(row)
        self._table.set_data(rows)
        self.main.status_bar.set_count(len(rows))

    # ═══════════════════════════════════════════════════════
    # ROW EVENTS
    # ═══════════════════════════════════════════════════════

    def _on_row_select(self, row_idx: int):
        pass  # Placeholder — hiển thị preview panel nếu cần

    def _on_row_double_click(self, row_idx: int):
        """Mở Invoice Detail View."""
        if 0 <= row_idx < len(self._invoices):
            inv = self._invoices[row_idx]
            from app.ui.views.invoice_detail_view import InvoiceDetailView
            InvoiceDetailView(self, inv, self.main)

    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════

    def _clear_data(self):
        self._invoices.clear()
        self._table.clear()
        self.main.status_bar.set_count(0)

    def _show_loading(self, msg=""):
        self._loading.place(relx=0.5, rely=0.5, anchor="center")
        self._loading.set_indeterminate(msg)
        self._loading.lift()

    def _hide_loading(self):
        self._loading.stop()
        self._loading.place_forget()
