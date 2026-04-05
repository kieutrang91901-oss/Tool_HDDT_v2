"""
InvoiceListView — Màn hình chính: Bảng danh sách HĐ + toolbar.

Tích hợp:
  - Tab Tổng hợp (Summary) / Chi tiết (Detail)
  - Tải bảng kê (query API, chọn mua vào/bán ra/cả hai)
  - Tải hóa đơn XML (download XML từ cổng thuế)
  - Import offline (XML/ZIP)
  - Export Excel
  - Column Config (riêng cho Summary và Detail)
"""
import customtkinter as ctk
import threading
import os
from tkinter import filedialog
from typing import List

from config.theme import get_colors, FONTS
from config.column_config import SUMMARY_COLUMNS_DEFAULT, DETAIL_COLUMNS_DEFAULT
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
    """Bảng danh sách hóa đơn — Màn hình chính với tab Tổng hợp / Chi tiết."""

    def __init__(self, parent, main_window, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color=colors["bg_primary"], **kwargs)
        self.main = main_window
        self.colors = colors
        self._invoices: List[InvoiceData] = []
        self._visible_invoices: List[InvoiceData] = []  # Danh sách đang hiển thị (sau filter)
        self._summary_columns: List[dict] = []
        self._detail_columns: List[dict] = []
        self._current_tab = "summary"
        self._last_summaries = []
        self._cancel_flag = False  # ESC cancel flag

        self._init_columns()
        self._build_ui()

    def _init_columns(self):
        """Load cột từ DB hoặc dùng mặc định (tách riêng summary/detail)."""
        # Summary columns
        stored_summary = self.main.db.get_columns("summary", visible_only=False)
        if stored_summary:
            self._summary_columns = [
                {"key": c.column_key, "name": c.display_name,
                 "format": c.format_type, "width": c.width,
                 "visible": c.is_visible, "is_dynamic": c.is_dynamic, "scope": c.scope}
                for c in stored_summary
            ]
        else:
            self._summary_columns = [dict(c) for c in SUMMARY_COLUMNS_DEFAULT]
            for i, c in enumerate(self._summary_columns):
                self.main.db.upsert_column(ColumnConfig(
                    column_key=c["key"], display_name=c["name"],
                    table_name="summary", is_visible=c["visible"],
                    sort_order=i, width=c["width"], format_type=c["format"],
                ))

        # Detail columns
        stored_detail = self.main.db.get_columns("detail", visible_only=False)
        if stored_detail:
            self._detail_columns = [
                {"key": c.column_key, "name": c.display_name,
                 "format": c.format_type, "width": c.width,
                 "visible": c.is_visible, "is_dynamic": c.is_dynamic, "scope": c.scope}
                for c in stored_detail
            ]
        else:
            self._detail_columns = [dict(c) for c in DETAIL_COLUMNS_DEFAULT]
            for i, c in enumerate(self._detail_columns):
                self.main.db.upsert_column(ColumnConfig(
                    column_key=c["key"], display_name=c["name"],
                    table_name="detail", is_visible=c["visible"],
                    sort_order=i, width=c["width"], format_type=c["format"],
                ))

    def _get_visible_columns(self, which: str = "summary") -> List[dict]:
        cols = self._summary_columns if which == "summary" else self._detail_columns
        return [c for c in cols if c.get("visible", True)]

    def _build_ui(self):
        c = self.colors

        # ── Toolbar ──────────────────────────────────
        self._toolbar = Toolbar(self)
        self._toolbar.pack(fill="x")

        self._toolbar.add_button("import", "Import", icon="📂", command=self._import_files, style="default")
        self._toolbar.add_button("query", "Tải bảng kê", icon="📥", command=self._show_query_menu, style="default")
        self._toolbar.add_button("download_xml", "Tải hóa đơn", icon="📄", command=self._download_selected_invoices, style="default")
        self._toolbar.add_separator()
        self._toolbar.add_button("export", "Export", icon="📤", command=self._show_export_menu)
        self._toolbar.add_button("view_inv", "View HĐ", icon="👁", command=self._view_selected_invoice)
        self._toolbar.add_separator()
        self._toolbar.add_button("columns", "Cột", icon="☰", command=self._open_column_chooser)
        self._toolbar.add_button("clear", "Xóa", command=self._clear_data)

        # ESC to cancel
        self.winfo_toplevel().bind("<Escape>", lambda e: self._cancel_operation())

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

        # ── Tab bar (Tổng hợp / Chi tiết) ─────────────
        tab_frame = ctk.CTkFrame(self, fg_color=c["bg_secondary"], height=40, corner_radius=0)
        tab_frame.pack(fill="x")
        tab_frame.pack_propagate(False)

        self._tab_summary_btn = ctk.CTkButton(
            tab_frame, text="📊 Tổng hợp", height=32,
            font=FONTS.get("body_bold", ("Segoe UI", 13, "bold")),
            fg_color=c["accent"], hover_color=c["accent_hover"],
            text_color="#ffffff", corner_radius=6,
            command=lambda: self._switch_tab("summary"),
        )
        self._tab_summary_btn.pack(side="left", padx=(8, 2), pady=4)

        self._tab_detail_btn = ctk.CTkButton(
            tab_frame, text="📋 Chi tiết", height=32,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_secondary"], corner_radius=6,
            command=lambda: self._switch_tab("detail"),
        )
        self._tab_detail_btn.pack(side="left", padx=2, pady=4)

        # Tab info label
        self._tab_info = ctk.CTkLabel(
            tab_frame, text="",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
        )
        self._tab_info.pack(side="right", padx=12)

        # ── Table container ──────────────────────────
        self._table_container = ctk.CTkFrame(self, fg_color=c["bg_primary"], corner_radius=0)
        self._table_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Summary table
        visible_summary = self._get_visible_columns("summary")
        self._summary_table = DataTable(
            self._table_container, columns=visible_summary,
            on_select=self._on_row_select,
            on_double_click=self._on_row_double_click,
        )
        self._summary_table.pack(fill="both", expand=True)

        # Detail table (hidden initially)
        visible_detail = self._get_visible_columns("detail")
        self._detail_table = DataTable(
            self._table_container, columns=visible_detail,
            on_select=self._on_detail_row_select,
        )
        # Don't pack detail table — it starts hidden

        # ── Loading overlay (hidden) ─────────────────
        self._loading = LoadingIndicator(self)

    # ═══════════════════════════════════════════════════════
    # TAB SWITCHING
    # ═══════════════════════════════════════════════════════

    def _switch_tab(self, tab: str):
        """Chuyển giữa tab Tổng hợp và Chi tiết."""
        if tab == self._current_tab:
            return

        c = self.colors
        self._current_tab = tab

        if tab == "summary":
            self._detail_table.pack_forget()
            self._summary_table.pack(fill="both", expand=True)
            self._tab_summary_btn.configure(
                fg_color=c["accent"], text_color="#ffffff",
                font=FONTS.get("body_bold", ("Segoe UI", 13, "bold")),
            )
            self._tab_detail_btn.configure(
                fg_color=c["bg_tertiary"], text_color=c["text_secondary"],
                font=FONTS.get("body", ("Segoe UI", 13)),
            )
            self._refresh_summary_table()
        else:
            self._summary_table.pack_forget()
            self._detail_table.pack(fill="both", expand=True)
            self._tab_detail_btn.configure(
                fg_color=c["accent"], text_color="#ffffff",
                font=FONTS.get("body_bold", ("Segoe UI", 13, "bold")),
            )
            self._tab_summary_btn.configure(
                fg_color=c["bg_tertiary"], text_color=c["text_secondary"],
                font=FONTS.get("body", ("Segoe UI", 13)),
            )
            self._refresh_detail_table()

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
        self._refresh_current_tab()

        ok = sum(1 for i in invoices if not i.parse_error)
        err = len(invoices) - ok
        msg = f"Đã import {ok} HĐ"
        if err > 0:
            msg += f" ({err} lỗi)"
        show_toast(self.main, msg, "success" if err == 0 else "warning")

    # ═══════════════════════════════════════════════════════
    # TẢI BẢNG KÊ (QUERY FROM API) — YÊU CẦU 4, 5
    # ═══════════════════════════════════════════════════════

    def _show_query_menu(self):
        """Hiện menu chọn loại HĐ cần tra cứu (mua vào / bán ra / cả hai)."""
        if not self.main.auth_service.is_logged_in:
            show_toast(self.main, "Vui lòng đăng nhập trước", "warning")
            return

        # Create popup menu
        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.configure(fg_color=self.colors["bg_secondary"])
        menu.attributes("-topmost", True)

        c = self.colors

        # Position menu below the button
        btn = self._toolbar.get_button("query")
        if btn:
            x = btn.winfo_rootx()
            y = btn.winfo_rooty() + btn.winfo_height() + 2
        else:
            x = self.winfo_rootx() + 100
            y = self.winfo_rooty() + 60

        # Menu border frame
        border = ctk.CTkFrame(menu, fg_color=c["border"], corner_radius=8)
        border.pack(fill="both", expand=True, padx=1, pady=1)

        inner = ctk.CTkFrame(border, fg_color=c["bg_secondary"], corner_radius=7)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        def _query(loai_list):
            menu.destroy()
            self._do_query(loai_list)

        # Menu items
        for text, loai_list in [
            ("📥  Mua vào", ["purchase"]),
            ("📤  Bán ra", ["sold"]),
            ("📦  Cả hai (mua + bán)", ["purchase", "sold"]),
        ]:
            ctk.CTkButton(
                inner, text=text, anchor="w",
                font=FONTS.get("body", ("Segoe UI", 13)),
                fg_color="transparent",
                hover_color=c["bg_tertiary"],
                text_color=c["text_primary"],
                height=36, corner_radius=4,
                command=lambda l=loai_list: _query(l),
            ).pack(fill="x", padx=4, pady=2)

        menu.geometry(f"220x130+{x}+{y}")

        # Auto close on focus loss
        def _close_menu(e=None):
            try:
                menu.destroy()
            except Exception:
                pass

        menu.bind("<FocusOut>", _close_menu)
        menu.after(100, lambda: menu.focus_set())

    def _do_query(self, loai_list: list):
        """Tra cứu HĐ từ cổng thuế — cursor pagination + bao gồm HĐ MTT.
        
        Tab-aware:
        - Tab Tổng Hợp: chỉ tải bảng kê summary (nhanh)
        - Tab Chi Tiết: tải summary + detail items cho từng HĐ
        """
        self._cancel_flag = False  # Reset cancel
        self._show_loading("Đang tra cứu...")
        tu, den = self._date_picker.get_api_format()
        need_detail = self._current_tab == "detail"

        def _query_thread():
            all_results = []
            seen_keys = set()

            def _progress_summary(count):
                self.after(0, lambda c=count:
                    self._loading.set_indeterminate(f"Đã tải {c} hóa đơn...")
                )

            for loai in loai_list:
                # 1) HĐ bình thường (endpoint /query/)
                normal = self.main.query_service.query_all_invoices(
                    loai, tu, den, is_sco=False, progress_cb=_progress_summary,
                )
                for inv in normal:
                    key = (inv.khhdon, inv.shdon)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append(inv)

                if normal:
                    self.main.query_service.cache_query_results(
                        self.main.auth_service.current_mst, normal
                    )

                # 2) HĐ máy tính tiền (endpoint /sco-query/)
                sco = self.main.query_service.query_all_invoices(
                    loai, tu, den, is_sco=True, progress_cb=_progress_summary,
                )
                for inv in sco:
                    key = (inv.khhdon, inv.shdon)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append(inv)

                if sco:
                    self.main.query_service.cache_query_results(
                        self.main.auth_service.current_mst, sco
                    )

            logger.info(f"Query complete: {len(all_results)} unique invoices")

            # Nếu đang ở tab Chi Tiết → tải detail items
            detail_map = {}
            if need_detail and all_results:
                self.after(0, lambda:
                    self._loading.set_indeterminate(
                        f"Đang tải chi tiết 0/{len(all_results)} HĐ..."
                    )
                )

                def _progress_detail(done, total):
                    self.after(0, lambda d=done, t=total:
                        self._loading.set_indeterminate(
                            f"Đang tải chi tiết {d}/{t} HĐ..."
                        )
                    )

                detail_map = self.main.query_service.fetch_invoice_details(
                    all_results, progress_cb=_progress_detail,
                )

            self.after(0, lambda: self._on_query_done(all_results, detail_map))

        threading.Thread(target=_query_thread, daemon=True).start()

    def _on_query_done(self, results, detail_map=None):
        self._hide_loading()
        count = len(results)

        # Lưu cache summary để dùng lại khi switch tab
        self._last_summaries = results

        if count > 0:
            converted = self._convert_summaries(results)

            # Gắn chi tiết hàng hóa vào InvoiceData nếu có
            if detail_map:
                for inv in converted:
                    key = f"{inv.ky_hieu}|{inv.so_hd}"
                    items = detail_map.get(key, [])
                    if items:
                        inv.hang_hoa = items

            self._invoices = converted
            self._refresh_current_tab()

        show_toast(self.main, f"Tìm thấy {count} hóa đơn", "success" if count > 0 else "info")
        self.main.status_bar.set_message(f"Đã tải {count} HĐ từ cổng thuế")

    @staticmethod
    def _convert_summaries(summaries) -> List[InvoiceData]:
        """Convert list of InvoiceSummary → InvoiceData for table display.
        
        Mapping theo De_Xuat_Bang_Du_Lieu.md.
        """
        # Mapping trạng thái HĐ (tthai) — Mục 2 đề xuất
        tthai_labels = {
            "1": "Hóa đơn mới",
            "2": "Hóa đơn thay thế",
            "3": "Hóa đơn điều chỉnh",
            "4": "HĐ đã bị thay thế",
            "5": "HĐ đã bị điều chỉnh",
            "6": "Hóa đơn đã hủy",
        }
        # Mapping kết quả xử lý CQT (ttxly)
        ttxly_labels = {
            "5": "Đã cấp mã hóa đơn",
            "6": "CQT không cấp mã",
            "8": "CQT đã nhận HĐ MTT",
        }
        # Nguồn tải API label
        nguon_labels = {
            "purchase": "HĐ mua vào",
            "sold": "HĐ bán ra",
        }

        converted = []
        for s in summaries:
            raw = s.raw_data
            tthai = str(raw.get("tthai", ""))
            ttxly = str(raw.get("ttxly", ""))

            # Nguồn tải: loại + trạng thái
            loai_label = nguon_labels.get(s.loai_hd, s.loai_hd)
            ttxly_label = ttxly_labels.get(ttxly, ttxly)
            is_sco = "SCO" in s.nha_cung_cap if hasattr(s, 'nha_cung_cap') else False
            nguon = f"{loai_label} - {'MTT' if ttxly == '8' else 'HĐĐT'} - {ttxly_label}"

            inv = InvoiceData(
                ky_hieu=s.khhdon,
                so_hd=s.shdon,
                ngay_lap=s.ngay_lap,
                mst_ban=s.mst_nban,
                ten_ban=s.ten_nban,
                mst_mua=s.mst_nmua,
                ten_mua=s.ten_nmua,
                dia_chi_ban=str(raw.get("nbdchi", "")),
                dia_chi_mua=str(raw.get("nmdchi", "")),
                tong_chua_thue=str(raw.get("tgtcthue", "")),
                tong_thue=str(raw.get("tgtthue", "")),
                tong_thanh_toan_so=str(raw.get("tgtttbso", "")),
                mau_so=str(raw.get("khmshdon", "1")),
                nha_cung_cap=f"API_{s.loai_hd.upper()}" if s.loai_hd else "API",
            )
            # Extra fields for column mapping
            inv.extras_header["id_hoa_don"] = str(raw.get("id", ""))
            inv.extras_header["trang_thai"] = tthai_labels.get(tthai, tthai)
            inv.extras_header["ttxly"] = ttxly_label
            inv.extras_header["nguon_tai"] = nguon
            converted.append(inv)
        return converted

    # ═══════════════════════════════════════════════════════
    # TẢI HÓA ĐƠN XML — CONCURRENT DOWNLOAD
    # ═══════════════════════════════════════════════════════

    def _download_selected_invoices(self):
        """Tải XML cho tất cả hóa đơn trong bảng kê hiện tại."""
        if not self.main.auth_service.is_logged_in:
            show_toast(self.main, "Vui lòng đăng nhập trước", "warning")
            return

        if not self._invoices:
            show_toast(self.main, "Không có hóa đơn để tải", "warning")
            return

        # Hiện thư mục lưu trữ
        account_mst = self.main.auth_service.current_mst
        from config.settings import DATA_DIR
        download_folder = os.path.join(DATA_DIR, "downloads", account_mst)
        os.makedirs(download_folder, exist_ok=True)
        self._last_download_folder = download_folder

        show_toast(
            self.main,
            f"Lưu tại: {download_folder}",
            "info",
        )

        # Tải tất cả hóa đơn trong bảng
        self._do_download_xml(list(range(len(self._invoices))))

    def _do_download_xml(self, indices: List[int]):
        """Tải XML hóa đơn song song (concurrent) theo danh sách indices."""
        invoices_to_dl = [self._invoices[i] for i in indices if 0 <= i < len(self._invoices)]
        if not invoices_to_dl:
            return

        total = len(invoices_to_dl)
        self._cancel_flag = False
        self._show_loading(f"Đang tải 0/{total} hóa đơn...")

        account_mst = self.main.auth_service.current_mst

        def _download_thread():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import time
            
            MAX_WORKERS = 3
            success = 0
            failed = 0
            errors = []       # HĐ lỗi
            ok_list = []      # HĐ thành công
            done_count = 0
            
            def _download_one(inv):
                return inv, self.main.query_service.download_xml(
                    nbmst=inv.mst_ban,
                    khhdon=inv.ky_hieu,
                    shdon=inv.so_hd,
                    account_mst=account_mst,
                    khmshdon=inv.mau_so or "1",
                )
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {}
                for i, inv in enumerate(invoices_to_dl):
                    if self._cancel_flag:
                        break
                    future = executor.submit(_download_one, inv)
                    futures[future] = inv
                    if i < total - 1:
                        time.sleep(0.15)
                
                for future in as_completed(futures):
                    if self._cancel_flag:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    inv, result = future.result()
                    done_count += 1
                    
                    if result.success:
                        success += 1
                        inv.file_path = result.file_path
                        ok_list.append(f"{inv.ky_hieu}-{inv.so_hd}")
                    else:
                        failed += 1
                        err_msg = result.error_msg or "Lỗi không xác định"
                        errors.append(f"{inv.ky_hieu}-{inv.so_hd}: {err_msg}")
                    
                    self.after(0, lambda s=success, f=failed, d=done_count: (
                        self._loading.set_progress(d, total, f"Tải {d}/{total} (OK: {s}, Lỗi: {f})")
                    ))

            self.after(0, lambda: self._on_download_done(success, failed, errors))

        threading.Thread(target=_download_thread, daemon=True).start()

    def _on_download_done(self, success: int, failed: int, errors: list = None):
        self._hide_loading()

        # Log errors
        if errors:
            for err in errors:
                logger.warning(f"Download error: {err}")

        # Hiện dialog kết quả chi tiết
        self._show_download_result_dialog(success, failed, errors or [])

    def _show_download_result_dialog(self, success: int, failed: int, errors: list):
        """Hiện dialog tổng hợp kết quả tải + hỏi mở folder + xuất DS lỗi."""
        import customtkinter as ctk
        from config.theme import get_colors, FONTS

        download_folder = getattr(self, '_last_download_folder', '')
        colors = get_colors()

        # Tạo message
        lines = [f"✅ Thành công: {success} hóa đơn"]
        if failed > 0:
            lines.append(f"❌ Lỗi: {failed} hóa đơn")
            lines.append("")
            lines.append("Chi tiết lỗi:")
            for err in errors[:10]:
                lines.append(f"  • {err}")
            if len(errors) > 10:
                lines.append(f"  ... và {len(errors) - 10} lỗi khác")
        if download_folder:
            lines.append("")
            lines.append(f"📁 Thư mục: {download_folder}")

        message = "\n".join(lines)

        # Custom dialog
        dlg = ctk.CTkToplevel(self)
        dlg.title("Kết quả tải hóa đơn")
        line_count = message.count("\n") + 1
        dlg_h = max(220, min(500, 80 + line_count * 20 + 80))
        dlg_w = 520
        dlg.geometry(f"{dlg_w}x{dlg_h}")
        dlg.resizable(False, False)
        dlg.configure(fg_color=colors["bg_primary"])
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ctk.CTkLabel(
            dlg, text=message,
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=colors["text_primary"],
            wraplength=dlg_w - 40, justify="left", anchor="nw",
        ).pack(padx=20, pady=(20, 10), fill="both", expand=True)

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 16), fill="x")

        # Nút Đóng
        ctk.CTkButton(
            btn_frame, text="Đóng", width=80,
            fg_color=colors["bg_tertiary"], hover_color=colors["border"],
            text_color=colors["text_primary"],
            command=dlg.destroy,
        ).pack(side="right", padx=(6, 0))

        # Nút Mở Folder
        ctk.CTkButton(
            btn_frame, text="📁 Mở folder", width=110,
            fg_color=colors["accent"], hover_color=colors["accent_hover"],
            command=lambda: (self._open_download_folder(download_folder), dlg.destroy()),
        ).pack(side="right", padx=(6, 0))

        # Nút Xuất DS Lỗi (chỉ hiện khi có lỗi)
        if errors:
            ctk.CTkButton(
                btn_frame, text="📋 Xuất DS lỗi", width=120,
                fg_color=colors["error"], hover_color="#dc2626",
                command=lambda: self._export_error_list(errors, dlg),
            ).pack(side="right")

        # Center dialog
        dlg.update_idletasks()
        parent = self.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - dlg_w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dlg_h) // 2
        dlg.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")

        self.main.status_bar.set_message(
            f"Tải xong: {success} OK, {failed} lỗi"
        )

    def _export_error_list(self, errors: list, parent_dlg=None):
        """Xuất danh sách hóa đơn lỗi ra file .txt."""
        path = filedialog.asksaveasfilename(
            parent=parent_dlg or self,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="DS_HoaDon_Loi.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("DANH SÁCH HÓA ĐƠN TẢI LỖI\n")
                f.write("=" * 50 + "\n\n")
                for i, err in enumerate(errors, 1):
                    f.write(f"{i}. {err}\n")
                f.write(f"\nTổng: {len(errors)} hóa đơn lỗi\n")
            show_toast(self.main, f"Đã xuất {len(errors)} lỗi → {os.path.basename(path)}", "success")
        except Exception as e:
            show_toast(self.main, f"Lỗi xuất: {e}", "error")

    def _open_download_folder(self, folder: str):
        """Mở thư mục download trong Explorer."""
        if folder and os.path.isdir(folder):
            os.startfile(folder)

    # ═══════════════════════════════════════════════════════
    # EXPORT
    # ═══════════════════════════════════════════════════════

    def _show_export_menu(self):
        """Dropdown menu: Export TH / CT / TH+CT."""
        btn = self._toolbar.get_button("export")
        if not btn:
            return
        menu = tk.Menu(self.winfo_toplevel(), tearoff=0,
                       bg=self.colors["bg_secondary"], fg=self.colors["text_primary"],
                       font=("Segoe UI", 11))
        menu.add_command(label="📊 Export Tổng Hợp", command=self._export_summary)
        menu.add_command(label="📋 Export Chi Tiết", command=self._export_detail)
        menu.add_separator()
        menu.add_command(label="📦 Export TH + CT", command=self._export_both)
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        menu.post(x, y)
        menu.after(100, lambda: menu.focus_set())

    def _export_both(self):
        """Export cả tổng hợp và chi tiết vào 2 sheet trong 1 file."""
        if not self._invoices:
            show_toast(self.main, "Không có dữ liệu để export", "warning")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="HDDT_TongHop_ChiTiet.xlsx",
        )
        if not path:
            return

        s_cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                  for c in self._get_visible_columns("summary")]
        d_cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                  for c in self._get_visible_columns("detail")]

        result = self.main.excel_service.export_detail(self._invoices, path, s_cols, d_cols)
        if result["success"]:
            show_toast(self.main, f"Đã export TH+CT: {result['row_count']} dòng", "success")
            os.startfile(path)
        else:
            show_toast(self.main, f"Lỗi export: {result['error_msg']}", "error")

    def _view_selected_invoice(self):
        """View trực quan hóa đơn (qua trình duyệt web)."""
        try:
            import zipfile
            import shutil
            import webbrowser

            rows = self._summary_table.get_selected_rows()
            if not rows:
                show_toast(self.main, "Vui lòng chọn 1 hóa đơn trong danh sách", "info")
                return
            target = self._visible_invoices if self._visible_invoices else self._invoices
            row_idx = rows[0]
            if not (0 <= row_idx < len(target)):
                return
            inv = target[row_idx]

            def get_html_from_folder(folder_path):
                if not os.path.exists(folder_path):
                    return None
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        logger.info(f"Checking file for visual view: {file}")
                        if file.lower().endswith('.html') and 'invoice' in file.lower():
                            return os.path.join(root, file)
                        if file.lower() == 'invoice.html':
                            return os.path.join(root, file)
                return None

            def _open_visual(path):
                try:
                    html_file = None
                    if path and path.lower().endswith(".zip"):
                        temp_dir = os.path.join(self.main.query_service._download_base, "temp_view", f"{inv.ky_hieu}_{inv.so_hd}")
                        os.makedirs(temp_dir, exist_ok=True)
                        with zipfile.ZipFile(path, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                        html_file = get_html_from_folder(temp_dir)
                        if not html_file:
                            show_toast(self.main, "Không tìm thấy file HTML chứa giao diện hiển thị trong gói ZIP tải về", "error")
                    elif path and os.path.isdir(path):
                        html_file = get_html_from_folder(path)
                        if not html_file:
                            show_toast(self.main, "Không tìm thấy file giao diện HTML trong thư mục import", "error")
                    elif path and path.lower().endswith(".xml"):
                        html_file = get_html_from_folder(os.path.dirname(path))
                        if not html_file:
                            show_toast(self.main, "Không tìm thấy file giao diện HTML đi kèm hóa đơn (do chưa có file gốc tải về)", "error")
                    else:
                        show_toast(self.main, f"Định dạng file ({path}) không được hỗ trợ mở trình duyệt", "error")

                    if html_file:
                        try:
                            # Ưu tiên ưu dùng os.startfile trên Windows vì nó gọi trực tiếp ứng dụng mặc định
                            os.startfile(html_file)
                        except Exception as e1:
                            logger.error(f"os.startfile error: {e1}")
                            # Dự phòng
                            webbrowser.open_new_tab(f"file:///{os.path.abspath(html_file).replace(os.path.sep, '/')}")
                except Exception as e:
                    logger.error(f"Lỗi mở giao diện: {e}", exc_info=True)
                    show_toast(self.main, f"Có lỗi xảy ra khi tạo giao diện review tĩnh: {e}", "error")

            xml_path = getattr(inv, "xml_path", None)
            if not xml_path:
                xml_path = getattr(inv, "file_path", None)

            if xml_path and os.path.exists(xml_path):
                _open_visual(xml_path)
            else:
                self._show_loading("Đang yêu cầu bản tin trực quan từ Thuế...")
                def _dl_and_view():
                    try:
                        mst = self.main.auth_service.current_mst
                        res = self.main.query_service.download_xml(
                            nbmst=inv.mst_ban,
                            khhdon=inv.ky_hieu,
                            shdon=inv.so_hd,
                            account_mst=mst,
                            khmshdon=inv.mau_so or "1",
                        )
                        self.after(0, self._hide_loading)
                        if res.success and res.file_path:
                            inv.xml_path = res.file_path
                            self.after(0, lambda: _open_visual(res.file_path))
                        else:
                            import urllib.parse
                            err = urllib.parse.unquote(res.error_msg) if res.error_msg else "Lỗi không rõ từ Cổng Thuế"
                            self.after(0, lambda: show_toast(self.main, f"Thuế từ chối trả về giao diện gốc: {err}", "warning"))
                    except Exception as e:
                        logger.error(f"Error in _dl_and_view: {e}", exc_info=True)
                        self.after(0, self._hide_loading)
                        self.after(0, lambda e=e: show_toast(self.main, f"Lỗi tải XML: {e}", "error"))

                threading.Thread(target=_dl_and_view, daemon=True).start()
        except Exception as e:
            logger.error(f"Critical error in _view_selected_invoice: {e}")
            show_toast(self.main, f"Lỗi chức năng: {e}", "error")

    def _cancel_operation(self):
        """ESC — dừng tất cả lệnh đang chạy."""
        self._cancel_flag = True
        self._hide_loading()
        show_toast(self.main, "Đã hủy thao tác", "info")

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
                for c in self._get_visible_columns("summary")]

        result = self.main.excel_service.export_summary(self._invoices, path, cols)
        if result["success"]:
            show_toast(self.main, f"Đã export {result['row_count']} dòng", "success")
            os.startfile(path)
        else:
            show_toast(self.main, f"Lỗi export: {result['error_msg']}", "error")

    def _export_portal_excel(self):
        """Tải bảng kê Excel trực tiếp từ cổng thuế (giống format web)."""
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="DANH_SACH_HOA_DON.xlsx",
        )
        if not path:
            return

        tu, den = self._date_picker.get_api_format()
        self._show_loading("Đang tải bảng kê từ cổng thuế...")

        def _thread():
            ok = self.main.query_service.export_excel_from_portal(tu, den, path)
            self.after(0, lambda: self._on_portal_export_done(ok, path))

        threading.Thread(target=_thread, daemon=True).start()

    def _on_portal_export_done(self, success: bool, path: str):
        self._hide_loading()
        if success:
            show_toast(self.main, f"Đã tải bảng kê → {os.path.basename(path)}", "success")
            os.startfile(path)
        else:
            show_toast(self.main, "Không tải được bảng kê từ cổng thuế", "error")

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

        s_cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                  for c in self._get_visible_columns("summary")]
        d_cols = [ColumnConfig(column_key=c["key"], display_name=c["name"], format_type=c["format"], width=c["width"])
                  for c in self._get_visible_columns("detail")]

        result = self.main.excel_service.export_detail(self._invoices, path, s_cols, d_cols)
        if result["success"]:
            show_toast(self.main, f"Đã export {result['row_count']} dòng chi tiết", "success")
            os.startfile(path)
        else:
            show_toast(self.main, f"Lỗi export: {result['error_msg']}", "error")

    # ═══════════════════════════════════════════════════════
    # COLUMN CHOOSER — TÁCH RIÊNG SUMMARY / DETAIL
    # ═══════════════════════════════════════════════════════

    def _open_column_chooser(self):
        """Mở column chooser theo tab đang active."""
        if self._current_tab == "summary":
            self._open_summary_column_chooser()
        else:
            self._open_detail_column_chooser()

    def _open_summary_column_chooser(self):
        configs = [
            ColumnConfig(
                column_key=c["key"], display_name=c["name"],
                table_name="summary", is_visible=c.get("visible", True),
                sort_order=i, width=c.get("width", 120),
                format_type=c.get("format", "text"),
                is_dynamic=c.get("is_dynamic", False), scope=c.get("scope", ""),
            )
            for i, c in enumerate(self._summary_columns)
        ]
        ColumnChooser(
            self, configs,
            on_apply=self._apply_summary_columns,
            on_reset=self._reset_summary_columns,
            title="Cấu hình cột — Tổng hợp",
        )

    def _open_detail_column_chooser(self):
        configs = [
            ColumnConfig(
                column_key=c["key"], display_name=c["name"],
                table_name="detail", is_visible=c.get("visible", True),
                sort_order=i, width=c.get("width", 120),
                format_type=c.get("format", "text"),
                is_dynamic=c.get("is_dynamic", False), scope=c.get("scope", ""),
            )
            for i, c in enumerate(self._detail_columns)
        ]
        ColumnChooser(
            self, configs,
            on_apply=self._apply_detail_columns,
            on_reset=self._reset_detail_columns,
            title="Cấu hình cột — Chi tiết",
        )

    def _apply_summary_columns(self, configs: List[ColumnConfig]):
        self._summary_columns = [
            {"key": c.column_key, "name": c.display_name, "format": c.format_type,
             "width": c.width, "visible": c.is_visible,
             "is_dynamic": c.is_dynamic, "scope": c.scope}
            for c in configs
        ]
        for i, c in enumerate(configs):
            c.sort_order = i
            c.table_name = "summary"
            self.main.db.upsert_column(c)

        self._summary_table.set_columns(self._get_visible_columns("summary"))
        self._refresh_summary_table()
        show_toast(self.main, "Cấu hình cột tổng hợp đã cập nhật", "success")

    def _reset_summary_columns(self):
        self._summary_columns = [dict(c) for c in SUMMARY_COLUMNS_DEFAULT]
        for i, c in enumerate(self._summary_columns):
            self.main.db.upsert_column(ColumnConfig(
                column_key=c["key"], display_name=c["name"],
                table_name="summary", is_visible=c["visible"],
                sort_order=i, width=c["width"], format_type=c["format"],
            ))
        self._summary_table.set_columns(self._get_visible_columns("summary"))
        self._refresh_summary_table()
        show_toast(self.main, "Đã reset cột tổng hợp về mặc định", "info")

    def _apply_detail_columns(self, configs: List[ColumnConfig]):
        self._detail_columns = [
            {"key": c.column_key, "name": c.display_name, "format": c.format_type,
             "width": c.width, "visible": c.is_visible,
             "is_dynamic": c.is_dynamic, "scope": c.scope}
            for c in configs
        ]
        for i, c in enumerate(configs):
            c.sort_order = i
            c.table_name = "detail"
            self.main.db.upsert_column(c)

        self._detail_table.set_columns(self._get_visible_columns("detail"))
        self._refresh_detail_table()
        show_toast(self.main, "Cấu hình cột chi tiết đã cập nhật", "success")

    def _reset_detail_columns(self):
        self._detail_columns = [dict(c) for c in DETAIL_COLUMNS_DEFAULT]
        for i, c in enumerate(self._detail_columns):
            self.main.db.upsert_column(ColumnConfig(
                column_key=c["key"], display_name=c["name"],
                table_name="detail", is_visible=c["visible"],
                sort_order=i, width=c["width"], format_type=c["format"],
            ))
        self._detail_table.set_columns(self._get_visible_columns("detail"))
        self._refresh_detail_table()
        show_toast(self.main, "Đã reset cột chi tiết về mặc định", "info")

    # ═══════════════════════════════════════════════════════
    # TABLE DATA — SUMMARY
    # ═══════════════════════════════════════════════════════

    def _refresh_current_tab(self):
        """Refresh bảng hiện tại."""
        if self._current_tab == "summary":
            self._refresh_summary_table()
        else:
            self._refresh_detail_table()

    def _refresh_summary_table(self):
        """Refresh bảng tổng hợp."""
        self._visible_invoices = list(self._invoices)  # Track visible
        visible = self._get_visible_columns("summary")
        rows = []
        for idx, inv in enumerate(self._invoices, 1):
            row = [self._get_summary_value(inv, col["key"], idx) for col in visible]
            rows.append(row)

        self._summary_table.set_data(rows)
        self.main.status_bar.set_count(len(rows))
        self._tab_info.configure(text=f"{len(self._invoices)} hóa đơn")

    def _get_summary_value(self, inv: InvoiceData, key: str, idx: int):
        """Lấy giá trị 1 ô bảng tổng hợp — theo De_Xuat_Bang_Du_Lieu."""
        mapping = {
            "stt": idx,
            # Cột bắt buộc
            "ky_hieu": inv.ky_hieu,
            "so_hd": inv.so_hd,
            "ngay_lap": inv.ngay_lap,
            "mst_ban": inv.mst_ban,
            "ten_ban": inv.ten_ban,
            "mst_mua": inv.mst_mua,
            "ten_mua": inv.ten_mua,
            "tong_thanh_toan": inv.tong_thanh_toan_so,
            "trang_thai": inv.extras_header.get("trang_thai", ""),
            "ttxly": inv.extras_header.get("ttxly", ""),
            # Cột tùy chọn
            "id_hoa_don": inv.extras_header.get("id_hoa_don", ""),
            "nguon_tai": inv.extras_header.get("nguon_tai", ""),
            "dia_chi_ban": inv.dia_chi_ban,
            "dia_chi_mua": inv.dia_chi_mua,
            "tong_chua_thue": inv.tong_chua_thue,
            "tong_thue": inv.tong_thue,
            "mau_so": inv.mau_so,
        }
        if key in mapping:
            return mapping[key]
        # Dynamic extras fallback
        return inv.extras_header.get(key, "")

    # ═══════════════════════════════════════════════════════
    # TABLE DATA — DETAIL (hàng hóa)
    # ═══════════════════════════════════════════════════════

    def _refresh_detail_table(self):
        """Refresh bảng chi tiết hàng hóa."""
        visible = self._get_visible_columns("detail")
        rows = []
        stt = 0
        for inv in self._invoices:
            for hh in inv.hang_hoa:
                stt += 1
                row = [self._get_detail_value(inv, hh, col["key"], stt) for col in visible]
                rows.append(row)

        self._detail_table.set_data(rows)
        self._tab_info.configure(text=f"{stt} dòng hàng hóa từ {len(self._invoices)} HĐ")

    def _get_detail_value(self, inv: InvoiceData, hh, key: str, idx: int):
        """Lấy giá trị 1 ô bảng chi tiết hàng hóa."""
        mapping = {
            "stt": idx,
            # Header context (invoice-level)
            "ky_hieu": inv.ky_hieu,
            "so_hd": inv.so_hd,
            "ngay_lap": inv.ngay_lap,
            "mst_ban": inv.mst_ban,
            "ten_ban": inv.ten_ban,
            # Item-level
            "tinh_chat": hh.tinh_chat,
            "ma_hang": hh.ma_hang,
            "ten_hang": hh.ten_hang,
            "don_vi_tinh": hh.don_vi_tinh,
            "so_luong": hh.so_luong,
            "don_gia": hh.don_gia,
            "ty_le_ck": hh.ty_le_ck,
            "so_tien_ck": hh.so_tien_ck,
            "thanh_tien": hh.thanh_tien,
            "thue_suat": hh.thue_suat,
            # Tiền thuế: lấy từ extras (VATAmount) hoặc tính toán
            "tien_thue": hh.extras.get("VATAmount", hh.extras.get("tien_thue", "")),
        }
        if key in mapping:
            return mapping[key]
        # Dynamic extras from item
        return hh.extras.get(key, "")

    # ═══════════════════════════════════════════════════════
    # SEARCH / FILTER
    # ═══════════════════════════════════════════════════════

    def _do_search(self, text: str):
        if not text:
            self._refresh_current_tab()
            return
        text_lower = text.lower()
        filtered = [
            inv for inv in self._invoices
            if text_lower in inv.ten_ban.lower()
            or text_lower in inv.mst_ban.lower()
            or text_lower in inv.so_hd.lower()
            or text_lower in inv.ky_hieu.lower()
        ]
        if self._current_tab == "summary":
            self._show_filtered_summary(filtered)
        else:
            self._show_filtered_detail(filtered)

    def _show_filtered_summary(self, invoices):
        self._visible_invoices = invoices  # Track filtered list
        visible = self._get_visible_columns("summary")
        rows = []
        for idx, inv in enumerate(invoices, 1):
            row = [self._get_summary_value(inv, c["key"], idx) for c in visible]
            rows.append(row)
        self._summary_table.set_data(rows)
        self.main.status_bar.set_count(len(rows))

    def _show_filtered_detail(self, invoices):
        visible = self._get_visible_columns("detail")
        rows = []
        stt = 0
        for inv in invoices:
            for hh in inv.hang_hoa:
                stt += 1
                row = [self._get_detail_value(inv, hh, c["key"], stt) for c in visible]
                rows.append(row)
        self._detail_table.set_data(rows)

    # ═══════════════════════════════════════════════════════
    # ROW EVENTS
    # ═══════════════════════════════════════════════════════

    def _on_row_select(self, row_idx: int):
        pass

    def _on_row_double_click(self, row_idx: int):
        """Mở Invoice Detail View — dùng _visible_invoices để tránh lệch index khi search."""
        target = self._visible_invoices if self._visible_invoices else self._invoices
        if 0 <= row_idx < len(target):
            inv = target[row_idx]
            from app.ui.views.invoice_detail_view import InvoiceDetailView
            InvoiceDetailView(self, inv, self.main)

    def _on_detail_row_select(self, row_idx: int):
        pass

    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════

    def _clear_data(self):
        self._invoices.clear()
        self._summary_table.clear()
        self._detail_table.clear()
        self.main.status_bar.set_count(0)
        self._tab_info.configure(text="")

    def _show_loading(self, msg=""):
        self._loading.place(relx=0.5, rely=0.5, anchor="center")
        self._loading.set_indeterminate(msg)
        self._loading.lift()

    def _hide_loading(self):
        self._loading.stop()
        self._loading.place_forget()
