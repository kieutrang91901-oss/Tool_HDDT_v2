"""
InvoiceDetailView — Popup chi tiết 1 hóa đơn.

Hiển thị:
- Header info (Ký hiệu, Số HĐ, Ngày lập, MCCQT...)
- Người bán / Người mua
- Bảng hàng hóa (DataTable)
- Tổng kết
- Thông tin tra cứu (Fkey, Portal Link)
- Extras (dynamic fields)
"""
import customtkinter as ctk
from typing import Optional

from config.theme import get_colors, FONTS
from config.column_config import DETAIL_COLUMNS_DEFAULT
from config.logger import get_logger
from app.models.entities import InvoiceData
from app.ui.components.data_table import DataTable

logger = get_logger(__name__)


class InvoiceDetailView(ctk.CTkToplevel):
    """Popup chi tiết HĐ — mở khi double-click dòng trong bảng."""

    def __init__(self, parent, invoice: InvoiceData, main_window=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.inv = invoice
        self.main = main_window
        self.colors = get_colors()

        self.title(f"Chi tiết HĐ: {invoice.ky_hieu}-{invoice.so_hd}")
        self.geometry("900x650")
        self.configure(fg_color=self.colors["bg_primary"])
        self.transient(parent.winfo_toplevel())

        self._build_ui()
        self._center()

    def _build_ui(self):
        c = self.colors

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color=c["bg_primary"])
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # ── Header Info ──────────────────────────────
        self._section(scroll, "Thông tin hóa đơn")
        info_grid = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
        info_grid.pack(fill="x", pady=(0, 12))

        info_data = [
            ("Vendor", self.inv.nha_cung_cap),
            ("Mẫu số", self.inv.mau_so),
            ("Ký hiệu", self.inv.ky_hieu),
            ("Số HĐ", self.inv.so_hd),
            ("Ngày lập", self.inv.ngay_lap),
            ("Loại HĐ", self.inv.ten_loai_hd),
            ("HTTT", self.inv.httt),
            ("DVT Tiền tệ", self.inv.don_vi_tien_te),
            ("MCCQT", self.inv.mccqt),
            ("Trạng thái", f"{self.inv.status_label}"),
        ]
        self._render_grid(info_grid, info_data, cols=2)

        # ── Người bán ────────────────────────────────
        self._section(scroll, "Người bán")
        seller_grid = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
        seller_grid.pack(fill="x", pady=(0, 12))

        seller_data = [
            ("Tên", self.inv.ten_ban),
            ("MST", self.inv.mst_ban),
            ("Địa chỉ", self.inv.dia_chi_ban),
            ("Email", self.inv.email_ban),
            ("SĐT", self.inv.dien_thoai_ban),
            ("Tài khoản", f"{self.inv.so_tk_ban} - {self.inv.ten_ngan_hang_ban}" if self.inv.so_tk_ban else ""),
        ]
        self._render_grid(seller_grid, seller_data, cols=1)

        # ── Người mua ────────────────────────────────
        self._section(scroll, "Người mua")
        buyer_grid = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
        buyer_grid.pack(fill="x", pady=(0, 12))

        buyer_data = [
            ("Tên", self.inv.ten_mua),
            ("MST", self.inv.mst_mua),
            ("Địa chỉ", self.inv.dia_chi_mua),
            ("Người mua hàng", self.inv.ho_ten_nguoi_mua),
            ("Mã KH", self.inv.ma_khach_hang),
        ]
        self._render_grid(buyer_grid, buyer_data, cols=1)

        # ── Hàng hóa ────────────────────────────────
        self._section(scroll, f"Hàng hóa/Dịch vụ ({len(self.inv.hang_hoa)} dòng)")

        detail_cols = [
            {"key": c["key"], "name": c["name"], "format": c["format"], "width": c["width"]}
            for c in DETAIL_COLUMNS_DEFAULT if c["visible"]
        ]

        table = DataTable(scroll, columns=detail_cols, height=min(200, 40 + len(self.inv.hang_hoa) * 25))
        table.pack(fill="x", pady=(0, 12))

        rows = []
        for h in self.inv.hang_hoa:
            rows.append([
                h.stt, h.tinh_chat, h.ma_hang, h.ten_hang,
                h.don_vi_tinh, h.so_luong, h.don_gia,
                h.thue_suat, h.thanh_tien,
            ])
        table.set_data(rows)

        # ── Tổng kết ────────────────────────────────
        self._section(scroll, "Tổng kết")
        total_grid = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
        total_grid.pack(fill="x", pady=(0, 12))

        from config.theme import format_number
        total_data = [
            ("Tổng chưa thuế", format_number(self.inv.tong_chua_thue, "currency")),
            ("Tổng thuế", format_number(self.inv.tong_thue, "currency")),
            ("Tổng thanh toán", format_number(self.inv.tong_thanh_toan_so, "currency")),
            ("Bằng chữ", self.inv.tong_thanh_toan_chu),
        ]
        self._render_grid(total_grid, total_data, cols=1)

        # ── Tra cứu ─────────────────────────────────
        if self.inv.fkey or self.inv.portal_link:
            self._section(scroll, "Thông tin tra cứu")
            lookup_grid = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
            lookup_grid.pack(fill="x", pady=(0, 12))

            lookup_data = [
                (self.inv.fkey_label, self.inv.fkey),
                ("Portal Link", self.inv.portal_link),
                ("Search Key", self.inv.search_key),
            ]
            self._render_grid(lookup_grid, [(k, v) for k, v in lookup_data if v], cols=1)

        # ── Extras (Dynamic) ────────────────────────
        all_extras = self.inv.get_all_extras()
        has_extras = any(v for v in all_extras.values())
        if has_extras:
            self._section(scroll, "Thông tin bổ sung (TTKhac)")
            for scope, extras in all_extras.items():
                if extras:
                    scope_labels = {
                        "header": "Header", "seller": "Người bán",
                        "buyer": "Người mua", "payment": "Thanh toán",
                        "invoice": "Hóa đơn",
                    }
                    label = scope_labels.get(scope, scope)
                    ext_frame = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
                    ext_frame.pack(fill="x", pady=(0, 8))

                    ctk.CTkLabel(
                        ext_frame, text=f"[{label}]",
                        font=FONTS.get("caption", ("Segoe UI", 11)),
                        text_color=c["accent_light"],
                    ).pack(anchor="w", padx=16, pady=(8, 0))

                    self._render_grid(ext_frame, list(extras.items()), cols=1, pad_top=0)

    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════

    def _section(self, parent, title: str):
        ctk.CTkLabel(
            parent, text=title,
            font=FONTS.get("heading_sm", ("Segoe UI", 14, "bold")),
            text_color=self.colors["accent"],
        ).pack(anchor="w", pady=(12, 4))

    def _render_grid(self, parent, data, cols=2, pad_top=12):
        c = self.colors
        for i, (label, value) in enumerate(data):
            if not value:
                continue
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(pad_top if i == 0 else 2, 2 if i < len(data) - 1 else 12))

            ctk.CTkLabel(
                row, text=f"{label}:",
                font=FONTS.get("body", ("Segoe UI", 13)),
                text_color=c["text_muted"],
                width=150 if cols == 2 else 180,
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=str(value),
                font=FONTS.get("body", ("Segoe UI", 13)),
                text_color=c["text_primary"],
                anchor="w",
                wraplength=500,
            ).pack(side="left", fill="x", expand=True)

    def _center(self):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - 900) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.geometry(f"+{x}+{y}")
