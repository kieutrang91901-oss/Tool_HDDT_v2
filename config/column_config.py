"""
Column Configuration — Định nghĩa cột mặc định và format types.

Cột Summary (bảng danh sách HĐ) và Detail (bảng hàng hóa)
đều cho phép user tự chọn hiển thị/ẩn.
"""

# ═══════════════════════════════════════════════════════
# FORMAT TYPES
# ═══════════════════════════════════════════════════════
# "text"     → hiển thị nguyên bản
# "number"   → format #,##0 (ví dụ: 1,234)
# "currency" → format #,##0 (VNĐ, không thập phân)
# "date"     → format DD/MM/YYYY

# ═══════════════════════════════════════════════════════
# BẢNG TỔNG HỢP (Summary) — Cột mặc định
# ═══════════════════════════════════════════════════════

SUMMARY_COLUMNS_DEFAULT = [
    {"key": "stt",              "name": "STT",              "format": "text",     "width": 50,  "visible": True},
    {"key": "ky_hieu",          "name": "Ký hiệu",         "format": "text",     "width": 100, "visible": True},
    {"key": "so_hd",            "name": "Số HĐ",           "format": "text",     "width": 100, "visible": True},
    {"key": "ngay_lap",         "name": "Ngày lập",        "format": "date",     "width": 110, "visible": True},
    {"key": "mst_ban",          "name": "MST NB",          "format": "text",     "width": 120, "visible": True},
    {"key": "ten_ban",          "name": "Tên NB",          "format": "text",     "width": 250, "visible": True},
    {"key": "mst_mua",          "name": "MST NM",          "format": "text",     "width": 120, "visible": False},
    {"key": "ten_mua",          "name": "Tên NM",          "format": "text",     "width": 250, "visible": False},
    {"key": "tong_chua_thue",   "name": "Tổng chưa thuế",  "format": "currency", "width": 130, "visible": True},
    {"key": "tong_thue",        "name": "Tổng thuế",       "format": "currency", "width": 120, "visible": True},
    {"key": "tong_thanh_toan",  "name": "Tổng TT",         "format": "currency", "width": 130, "visible": True},
    {"key": "trang_thai",       "name": "Trạng thái",      "format": "text",     "width": 100, "visible": True},
    {"key": "vendor",           "name": "Vendor",           "format": "text",     "width": 100, "visible": True},
    {"key": "mccqt",            "name": "MCCQT",            "format": "text",     "width": 150, "visible": False},
    {"key": "fkey",             "name": "Mã tra cứu",      "format": "text",     "width": 150, "visible": False},
    {"key": "portal_link",      "name": "Link tra cứu",    "format": "text",     "width": 200, "visible": False},
]

# ═══════════════════════════════════════════════════════
# BẢNG CHI TIẾT HÀNG HÓA (Detail) — Cột mặc định
# ═══════════════════════════════════════════════════════

DETAIL_COLUMNS_DEFAULT = [
    {"key": "stt",          "name": "STT",              "format": "text",     "width": 50,  "visible": True},
    {"key": "tinh_chat",    "name": "Tính chất",        "format": "text",     "width": 120, "visible": True},
    {"key": "ma_hang",      "name": "Mã hàng",         "format": "text",     "width": 120, "visible": True},
    {"key": "ten_hang",     "name": "Tên hàng",        "format": "text",     "width": 300, "visible": True},
    {"key": "don_vi_tinh",  "name": "ĐVT",             "format": "text",     "width": 80,  "visible": True},
    {"key": "so_luong",     "name": "Số lượng",        "format": "number",   "width": 100, "visible": True},
    {"key": "don_gia",      "name": "Đơn giá",         "format": "currency", "width": 120, "visible": True},
    {"key": "ty_le_ck",     "name": "TL Chiết khấu",   "format": "number",   "width": 100, "visible": False},
    {"key": "so_tien_ck",   "name": "ST Chiết khấu",   "format": "currency", "width": 120, "visible": False},
    {"key": "thue_suat",    "name": "Thuế suất",       "format": "text",     "width": 90,  "visible": True},
    {"key": "thanh_tien",   "name": "Thành tiền",      "format": "currency", "width": 130, "visible": True},
]

# ═══════════════════════════════════════════════════════
# HELPER: Lấy prefix cho dynamic column key
# ═══════════════════════════════════════════════════════

SCOPE_PREFIX = {
    "header":  "hdr_",
    "seller":  "slr_",
    "buyer":   "byr_",
    "item":    "itm_",
    "payment": "pmt_",
    "invoice": "inv_",
}


def make_dynamic_column_key(scope: str, field_key: str) -> str:
    """Tạo column_key cho dynamic field.
    
    Ví dụ: scope='header', field_key='PortalLink' → 'hdr_PortalLink'
    """
    prefix = SCOPE_PREFIX.get(scope, "ext_")
    return f"{prefix}{field_key}"


def parse_dynamic_column_key(column_key: str):
    """Parse dynamic column_key thành (scope, field_key).
    
    Ví dụ: 'hdr_PortalLink' → ('header', 'PortalLink')
    """
    for scope, prefix in SCOPE_PREFIX.items():
        if column_key.startswith(prefix):
            return scope, column_key[len(prefix):]
    return "", column_key
