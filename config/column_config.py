"""
Column Configuration — Định nghĩa cột mặc định cho Bảng Tổng Hợp và Bảng Chi Tiết.

Dựa theo:
- De_Xuat_Bang_Du_Lieu.md (Đặc tả cấu trúc dữ liệu)
- API fields từ /query/invoices/purchase|sold (Summary)
- API fields từ /query/invoices/detail > hdhhdvu[] (Detail items)
"""

# ═══════════════════════════════════════════════════════
# FORMAT TYPES
# ═══════════════════════════════════════════════════════
# "text"     → hiển thị nguyên bản
# "number"   → format #,##0 (ví dụ: 1,234)
# "currency" → format #,##0 (VNĐ, không thập phân)
# "date"     → format DD/MM/YYYY

# ═══════════════════════════════════════════════════════
# BẢNG TỔNG HỢP (Summary) — Mục 2 đề xuất
# Source: /query/invoices/purchase|sold
# ═══════════════════════════════════════════════════════

SUMMARY_COLUMNS_DEFAULT = [
    {"key": "stt",              "name": "STT",                   "format": "text",     "width": 50,  "visible": True},
    # ── Cột mặc định (bắt buộc hiện) ──────────────────
    {"key": "ky_hieu",          "name": "Ký hiệu HĐ",           "format": "text",     "width": 100, "visible": True},
    {"key": "so_hd",            "name": "Số hóa đơn",            "format": "text",     "width": 90,  "visible": True},
    {"key": "ngay_lap",         "name": "Ngày lập",              "format": "date",     "width": 110, "visible": True},
    {"key": "mst_ban",          "name": "MST Bên Bán",           "format": "text",     "width": 120, "visible": True},
    {"key": "ten_ban",          "name": "Tên Bên Bán",           "format": "text",     "width": 250, "visible": True},
    {"key": "mst_mua",          "name": "MST Bên Mua",           "format": "text",     "width": 120, "visible": True},
    {"key": "ten_mua",          "name": "Tên Bên Mua",           "format": "text",     "width": 250, "visible": True},
    {"key": "tong_thanh_toan",  "name": "Tổng Thanh Toán",       "format": "currency", "width": 140, "visible": True},
    {"key": "trang_thai",       "name": "Trạng Thái HĐ",         "format": "text",     "width": 130, "visible": True},
    {"key": "ttxly",            "name": "Kết Quả XL (CQT)",      "format": "text",     "width": 180, "visible": True},
    # ── Cột tùy chọn (mặc định ẩn) ────────────────────
    {"key": "id_hoa_don",       "name": "Mã Nội Bộ (ID)",        "format": "text",     "width": 100, "visible": False},
    {"key": "nguon_tai",        "name": "Nguồn Tải API",         "format": "text",     "width": 200, "visible": True},
    {"key": "dia_chi_ban",      "name": "Địa Chỉ Bên Bán",      "format": "text",     "width": 250, "visible": False},
    {"key": "dia_chi_mua",      "name": "Địa Chỉ Bên Mua",      "format": "text",     "width": 250, "visible": False},
    {"key": "tong_chua_thue",   "name": "Tổng Tiền Trước Thuế",  "format": "currency", "width": 140, "visible": False},
    {"key": "tong_thue",        "name": "Tổng Phí VAT",          "format": "currency", "width": 120, "visible": False},
    {"key": "mau_so",           "name": "Mẫu Số",                "format": "text",     "width": 60,  "visible": False},
]

# ═══════════════════════════════════════════════════════
# BẢNG CHI TIẾT (Detail) — Mục 3.2 đề xuất
# Source: /query/invoices/detail > hdhhdvu[]
#
# Mỗi dòng = 1 line item từ 1 hóa đơn.
# Header context (ky_hieu, so_hd) giúp nhận diện HĐ cha.
# ═══════════════════════════════════════════════════════

DETAIL_COLUMNS_DEFAULT = [
    {"key": "stt",          "name": "STT",               "format": "text",     "width": 50,  "visible": True},
    # ── Header context (invoice-level) ─────────────────
    {"key": "ky_hieu",      "name": "Ký hiệu HĐ",       "format": "text",     "width": 100, "visible": True},
    {"key": "so_hd",        "name": "Số HĐ",             "format": "text",     "width": 80,  "visible": True},
    {"key": "ngay_lap",     "name": "Ngày lập",          "format": "date",     "width": 100, "visible": False},
    {"key": "mst_ban",      "name": "MST NB",            "format": "text",     "width": 120, "visible": False},
    {"key": "ten_ban",      "name": "Tên NB",            "format": "text",     "width": 200, "visible": False},
    # ── Item-level (hdhhdvu[]) ─────────────────────────
    # Cột mặc định (bắt buộc hiện)
    {"key": "ten_hang",     "name": "Tên Hàng Hóa/DV",   "format": "text",     "width": 350, "visible": True},
    {"key": "thanh_tien",   "name": "Thành Tiền",        "format": "currency", "width": 130, "visible": True},
    # Cột tùy chọn
    {"key": "tinh_chat",    "name": "Tính Chất",         "format": "text",     "width": 100, "visible": True},
    {"key": "don_vi_tinh",  "name": "ĐVT",               "format": "text",     "width": 70,  "visible": True},
    {"key": "so_luong",     "name": "Số Lượng",          "format": "number",   "width": 90,  "visible": True},
    {"key": "don_gia",      "name": "Đơn Giá",           "format": "currency", "width": 120, "visible": True},
    {"key": "thue_suat",    "name": "Thuế Suất",         "format": "text",     "width": 80,  "visible": True},
    {"key": "tien_thue",    "name": "Tiền Thuế",         "format": "currency", "width": 110, "visible": True},
    {"key": "so_tien_ck",   "name": "Tiền CK/KM",        "format": "currency", "width": 110, "visible": False},
]


# ═══════════════════════════════════════════════════════
# COLUMN CONFIG ENTITY (DB)
# ═══════════════════════════════════════════════════════

from dataclasses import dataclass

@dataclass
class ColumnConfig:
    """Cấu hình 1 cột trên bảng, lưu DB để user custom."""
    column_key: str
    display_name: str
    format_type: str = "text"
    width: int = 100
    is_visible: bool = True
    sort_order: int = 0
    table_name: str = "summary"   # "summary" | "detail"
    is_dynamic: bool = False
    scope: str = ""               # "header" | "seller" | ... | ""


# ═══════════════════════════════════════════════════════
# DYNAMIC COLUMN UTILS
# ═══════════════════════════════════════════════════════

def parse_dynamic_column_key(key: str):
    """Parse key dạng 'scope__field' → (scope, field)."""
    if "__" in key:
        parts = key.split("__", 1)
        return parts[0], parts[1]
    return "", key
