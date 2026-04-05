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
        self._summary_columns: List[dict] = []
        self._detail_columns: List[dict] = []
        self._current_tab = "summary"

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
        """Tra cứu HĐ từ cổng thuế — cursor pagination + bao gồm HĐ MTT."""
        self._show_loading("Đang tra cứu...")
        tu, den = self._date_picker.get_api_format()

        def _query_thread():
            all_results = []
            seen_keys = set()

            def _progress(count):
                self.after(0, lambda c=count:
                    self._loading.set_indeterminate(f"Đã tải {c} hóa đơn...")
                )

            for loai in loai_list:
                # 1) HĐ bình thường (endpoint /query/)
                normal = self.main.query_service.query_all_invoices(
                    loai, tu, den, is_sco=False, progress_cb=_progress,
                )
                for inv in normal:
                    key = (inv.khhdon, inv.shdon)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append(inv)

                # Cache
                if normal:
                    self.main.query_service.cache_query_results(
                        self.main.auth_service.current_mst, normal
                    )

                # 2) HĐ máy tính tiền (endpoint /sco-query/)
                sco = self.main.query_service.query_all_invoices(
                    loai, tu, den, is_sco=True, progress_cb=_progress,
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
            self.after(0, lambda: self._on_query_done(all_results))

        threading.Thread(target=_query_thread, daemon=True).start()

    def _on_query_done(self, results):
        self._hide_loading()
        count = len(results)

        if count > 0:
            converted = self._convert_summaries(results)
            self._invoices = converted
            self._refresh_current_tab()

        show_toast(self.main, f"Tìm thấy {count} hóa đơn", "success" if count > 0 else "info")
        self.main.status_bar.set_message(f"Đã tải {count} HĐ từ cổng thuế")

    @staticmethod
    def _convert_summaries(summaries) -> List[InvoiceData]:
        """Convert list of InvoiceSummary → InvoiceData for table display.
        
        Mapping theo cấu trúc bảng kê cổng thuế (19 cột).
        Lưu ý: HĐ MTT không có tổng tiền phí và đơn vị tiền tệ.
        """
        # Mapping trạng thái HĐ (tthai)
        tthai_labels = {
            "1": "Hóa đơn mới",
            "2": "Hóa đơn thay thế",
            "3": "Hóa đơn điều chỉnh",
            "4": "Hóa đơn đã bị thay thế",
            "5": "Hóa đơn đã bị điều chỉnh",
            "6": "Hóa đơn đã hủy",
        }
        # Mapping kết quả kiểm tra (ttxly)
        ttxly_labels = {
            "5": "Đã cấp mã hóa đơn",
            "6": "CQT không cấp mã",
            "8": "CQT đã nhận - không mã",
        }

        converted = []
        for s in summaries:
            raw = s.raw_data
            inv = InvoiceData(
                ky_hieu=s.khhdon,
                so_hd=s.shdon,
                ngay_lap=s.ngay_lap,
                mst_ban=s.mst_nban,
                ten_ban=s.ten_nban,
                mst_mua=s.mst_nmua,
                ten_mua=s.ten_nmua,
                dia_chi_mua=str(raw.get("nmdchi", "")),
                tong_chua_thue=s.tong_tien_cthue,
                tong_thue=s.tong_tien_thue,
                tong_ck_tm=str(raw.get("tgtcktmai", "")),
                tong_thanh_toan_so=s.tong_thanh_toan,
                don_vi_tien_te=str(raw.get("dvtte", "")),
                ty_gia=str(raw.get("tgia", "")),
                nha_cung_cap=f"API_{s.loai_hd.upper()}" if s.loai_hd else "API",
                mau_so=str(raw.get("khmshdon", "1")),
            )
            # Extra fields
            tthai = str(raw.get("tthai", ""))
            ttxly = str(raw.get("ttxly", ""))
            inv.extras_header["trang_thai_label"] = tthai_labels.get(tthai, tthai)
            inv.extras_header["kq_kiem_tra"] = ttxly_labels.get(ttxly, ttxly)
            inv.extras_header["tong_phi"] = str(raw.get("tgtphi", ""))
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
                    future = executor.submit(_download_one, inv)
                    futures[future] = inv
                    if i < total - 1:
                        time.sleep(0.15)
                
                for future in as_completed(futures):
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
        visible = self._get_visible_columns("summary")
        rows = []
        for idx, inv in enumerate(self._invoices, 1):
            row = [self._get_summary_value(inv, col["key"], idx) for col in visible]
            rows.append(row)

        self._summary_table.set_data(rows)
        self.main.status_bar.set_count(len(rows))
        self._tab_info.configure(text=f"{len(self._invoices)} hóa đơn")

    def _get_summary_value(self, inv: InvoiceData, key: str, idx: int):
        """Lấy giá trị 1 ô bảng tổng hợp theo column key (19 cột cổng thuế)."""
        mapping = {
            "stt": idx,
            "mau_so": inv.mau_so,
            "ky_hieu": inv.ky_hieu,
            "so_hd": inv.so_hd,
            "ngay_lap": inv.ngay_lap,
            "mst_ban": inv.mst_ban,
            "ten_ban": inv.ten_ban,
            "mst_mua": inv.mst_mua,
            "ten_mua": inv.ten_mua,
            "dia_chi_mua": inv.dia_chi_mua,
            "tong_chua_thue": inv.tong_chua_thue,
            "tong_thue": inv.tong_thue,
            "tong_ck_tm": inv.tong_ck_tm,
            "tong_phi": inv.extras_header.get("tong_phi", ""),
            "tong_thanh_toan": inv.tong_thanh_toan_so,
            "don_vi_tien_te": inv.don_vi_tien_te,
            "ty_gia": inv.ty_gia,
            "trang_thai": inv.extras_header.get("trang_thai_label", ""),
            "kq_kiem_tra": inv.extras_header.get("kq_kiem_tra", ""),
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
        pass  # Placeholder

    def _on_row_double_click(self, row_idx: int):
        """Mở Invoice Detail View."""
        if 0 <= row_idx < len(self._invoices):
            inv = self._invoices[row_idx]
            from app.ui.views.invoice_detail_view import InvoiceDetailView
            InvoiceDetailView(self, inv, self.main)

    def _on_detail_row_select(self, row_idx: int):
        pass  # Placeholder

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
