"""
Data Models cho Tool HDDT v2.

Kiến trúc Two-Tier:
  - Tầng 1 (Fixed): Fields chuẩn TCVN — mọi hóa đơn đều có
  - Tầng 2 (Dynamic): Fields vendor-specific — tự phát hiện từ TTKhac/TTin[]

Tất cả entities trong file này KHÔNG phụ thuộc bất kỳ thư viện UI nào.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


# ══════════════════════════════════════════════════════════
# TÍNH CHẤT HÀNG HÓA (TChat)
# ══════════════════════════════════════════════════════════

TCHAT_LABEL = {
    "1": "Hàng hóa, dịch vụ",
    "2": "Hàng hóa đặc trưng",
    "3": "Khuyến mại",
    "4": "Chiết khấu",
    "5": "Hàng hóa đặc trưng",  # MISA dùng cho dịch vụ
}


# ══════════════════════════════════════════════════════════
# HÀNG HÓA / DỊCH VỤ — Từng dòng trong hóa đơn
# ══════════════════════════════════════════════════════════

@dataclass
class HangHoa:
    """Một dòng hàng hóa/dịch vụ trong hóa đơn.
    
    Tầng 1: Fields chuẩn TCVN (HHDVu).
    Tầng 2: extras — dict chứa tất cả TTKhac/TTin[] của dòng này.
    """
    # ── Tầng 1: TCVN Standard ────────────────────────────
    stt: str = ""
    tinh_chat_ma: str = ""          # Mã gốc: 1, 2, 3, 4, 5
    tinh_chat: str = ""             # Nhãn đã dịch (từ TCHAT_LABEL)
    ma_hang: str = ""               # MHHDVu
    ten_hang: str = ""              # THHDVu
    don_vi_tinh: str = ""           # DVTinh
    so_luong: str = ""              # SLuong
    don_gia: str = ""               # DGia
    ty_le_ck: str = ""              # TLCKhau — Tỷ lệ chiết khấu %
    so_tien_ck: str = ""            # STCKhau — Số tiền chiết khấu
    thue_suat: str = ""             # TSuat — 8%, 10%, 0%, KCT
    thanh_tien: str = ""            # ThTien — Thành tiền chưa thuế
    
    # ── Tầng 2: Vendor Dynamic (Auto-discovered) ────────
    extras: Dict[str, str] = field(default_factory=dict)
    # Chứa TẤT CẢ TTKhac/TTin[] trong HHDVu, ví dụ:
    # EasyInvoice: {"VATAmount": "8889", "Amount": "120000"}
    # MISA/GRAB:   {"BookingCode": "A-944...", "Vehicle": "50H-261.37"}
    # MISA/MTT:    {} (thường trống)
    # Vendor mới:  {bất kỳ key nào} — tự phát hiện


# ══════════════════════════════════════════════════════════
# BẢNG THUẾ SUẤT (LTSuat)
# ══════════════════════════════════════════════════════════

@dataclass
class LTSuat:
    """Một dòng trong bảng tổng hợp thuế suất."""
    thue_suat: str = ""     # TSuat
    thanh_tien: str = ""    # ThTien — Thành tiền theo mức
    tong_thue: str = ""     # TThue — Tiền thuế theo mức


# ══════════════════════════════════════════════════════════
# HÓA ĐƠN — Entity chính
# ══════════════════════════════════════════════════════════

@dataclass
class InvoiceData:
    """Dữ liệu đầy đủ của một hóa đơn điện tử.
    
    Tầng 1: Fields chuẩn TCVN — mọi vendor đều có.
    Tầng 2: extras_* — tự động trích xuất từ TTKhac ở các cấp khác nhau.
    
    Parser tự điền cả 2 tầng. UI và Export chỉ cần đọc.
    """
    
    # ── Metadata ─────────────────────────────────────────
    nha_cung_cap: str = "UNKNOWN"   # EASYINV | MISA_GTGT | MISA_MTT | VNPT | UNKNOWN
    
    # ── Tầng 1: Header chuẩn TCVN ───────────────────────
    mau_so: str = ""                # KHMSHDon — Mẫu số (1, 2...)
    ky_hieu: str = ""               # KHHDon — Ký hiệu (C26TVK, C26MGA...)
    so_hd: str = ""                 # SHDon — Số hóa đơn
    ngay_lap: str = ""              # NLap — Ngày lập (YYYY-MM-DD)
    ten_loai_hd: str = ""           # THDon — Tên loại HĐ
    httt: str = ""                  # HTTToan — Hình thức thanh toán
    don_vi_tien_te: str = ""        # DVTTe
    ty_gia: str = ""                # TGia
    mccqt: str = ""                 # MCCQT — Mã cơ quan thuế
    qr_content: str = ""            # DLQRCode
    mst_tcgp: str = ""              # MSTTCGP — MST tổ chức cung cấp PM
    
    # ── Tầng 1: Người bán ────────────────────────────────
    ten_ban: str = ""               # NBan/Ten
    mst_ban: str = ""               # NBan/MST
    dia_chi_ban: str = ""           # NBan/DChi
    email_ban: str = ""             # NBan/DCTDTu
    dien_thoai_ban: str = ""        # NBan/SDThoai
    so_tk_ban: str = ""             # NBan/STKNHang
    ten_ngan_hang_ban: str = ""     # NBan/TNHang
    ma_cua_hang: str = ""           # NBan/MCHang
    ten_cua_hang: str = ""          # NBan/TCHang
    
    # ── Tầng 1: Người mua ────────────────────────────────
    ten_mua: str = ""               # NMua/Ten
    mst_mua: str = ""               # NMua/MST
    dia_chi_mua: str = ""           # NMua/DChi
    ho_ten_nguoi_mua: str = ""      # NMua/HVTNMHang
    ma_khach_hang: str = ""         # NMua/MKHang
    cccd_nguoi_mua: str = ""        # NMua/CCCDan
    so_ho_chieu: str = ""           # NMua/SHChieu
    so_tk_mua: str = ""             # NMua/STKNHang
    
    # ── Tầng 1: Hàng hóa & Thuế suất ────────────────────
    hang_hoa: List[HangHoa] = field(default_factory=list)
    lt_suat: List[LTSuat] = field(default_factory=list)
    
    # ── Tầng 1: Tổng kết ────────────────────────────────
    tong_chua_thue: str = ""        # TgTCThue
    tong_thue: str = ""             # TgTThue
    tong_ck_tm: str = ""            # TTCKTMai — Chiết khấu thương mại
    tong_thanh_toan_so: str = ""    # TgTTTBSo
    tong_thanh_toan_chu: str = ""   # TgTTTBChu
    
    # ── Tầng 1: Chữ ký ──────────────────────────────────
    da_ky_nguoi_ban: bool = False
    ky_boi_nguoi_ban: str = ""
    ky_ngay_nguoi_ban: str = ""
    da_ky_cqt: bool = False
    ky_ngay_cqt: str = ""
    
    # ── Tầng 2: Vendor Dynamic (Auto-discovered) ────────
    # Parser tự động trích xuất TẤT CẢ TTKhac/TTin[]
    # ở mọi cấp (header, seller, buyer, payment, invoice).
    # Không cần biết trước vendor có fields gì.
    extras_header: Dict[str, str] = field(default_factory=dict)
    # TTChung/TTKhac — VD: {"PortalLink": "...", "Fkey": "...", "Mã số bí mật": "..."}
    
    extras_seller: Dict[str, str] = field(default_factory=dict)
    # NBan/TTKhac — VD: {"Tỉnh/Thành phố người bán": "TPHCM", ...}
    
    extras_buyer: Dict[str, str] = field(default_factory=dict)
    # NMua/TTKhac — VD: {"CusCode": "1000142556", "PaymentMethod": "Chuyển khoản"}
    
    extras_payment: Dict[str, str] = field(default_factory=dict)
    # TToan/TTKhac — VD: {"Tổng tiền thuế tiêu thụ đặc biệt": "0"}
    
    extras_invoice: Dict[str, str] = field(default_factory=dict)
    # HDon/TTKhac (ngoài cùng) — VD: {"SearchKey": "...", "MappingKey": "..."}
    
    # ── Runtime ──────────────────────────────────────────
    file_path: str = ""             # Đường dẫn file XML gốc
    html_path: str = ""             # Đường dẫn file HTML (nếu có)
    parse_error: str = ""           # Lỗi khi parse (rỗng = OK)
    
    # ═══════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ═══════════════════════════════════════════════════════
    
    @property
    def fkey(self) -> str:
        """Mã tra cứu HĐ — vị trí khác nhau tùy vendor."""
        # Ưu tiên: TTChung/TTKhac > HDon/TTKhac
        return (
            self.extras_header.get("Fkey", "")
            or self.extras_header.get("Mã số bí mật", "")
            or self.extras_invoice.get("Fkey", "")
            or ""
        )
    
    @property
    def portal_link(self) -> str:
        """Link portal tra cứu online (EasyInvoice)."""
        return self.extras_header.get("PortalLink", "")
    
    @property
    def search_key(self) -> str:
        """Search key (MISA_GTGT)."""
        return self.extras_invoice.get("SearchKey", "")
    
    @property
    def fkey_label(self) -> str:
        """Nhãn hiển thị cho mã tra cứu tùy vendor."""
        if self.nha_cung_cap == "MISA_MTT":
            return "Mã số bí mật"
        return "Fkey"
    
    @property
    def status_icon(self) -> str:
        """Icon trạng thái hóa đơn."""
        if self.parse_error:
            return "🔴"
        if not self.mccqt:
            return "❌"
        if self.nha_cung_cap == "MISA_MTT":
            return "🟢" if self.qr_content else "🟡"
        if not self.da_ky_nguoi_ban:
            return "⚠️"
        if not self.da_ky_cqt or not self.qr_content:
            return "🟡"
        return "✅"
    
    @property
    def status_label(self) -> str:
        """Nhãn trạng thái hóa đơn."""
        if self.parse_error:
            return "Lỗi đọc file"
        if not self.mccqt:
            return "Thiếu MCCQT"
        if self.nha_cung_cap == "MISA_MTT":
            return "Hợp lệ" if self.qr_content else "Hợp lệ một phần"
        if not self.da_ky_nguoi_ban:
            return "Chưa ký số"
        if not self.da_ky_cqt or not self.qr_content:
            return "Hợp lệ một phần"
        return "Hợp lệ"
    
    @property
    def display_title(self) -> str:
        """Tiêu đề hiển thị ngắn gọn."""
        return f"{self.ky_hieu}-{self.so_hd} | {self.ten_ban} | {self.ngay_lap}"
    
    def get_all_extras(self) -> Dict[str, Dict[str, str]]:
        """Trả về tất cả extras theo scope, phục vụ field_registry."""
        return {
            "header": self.extras_header,
            "seller": self.extras_seller,
            "buyer": self.extras_buyer,
            "payment": self.extras_payment,
            "invoice": self.extras_invoice,
        }
    
    def get_item_extras_keys(self) -> set:
        """Trả về tất cả unique keys từ extras của hàng hóa."""
        keys = set()
        for item in self.hang_hoa:
            keys.update(item.extras.keys())
        return keys


# ══════════════════════════════════════════════════════════
# TÀI KHOẢN (Account)
# ══════════════════════════════════════════════════════════

@dataclass
class Account:
    """Tài khoản đăng nhập cổng thuế (1 MST = 1 tài khoản)."""
    id: int = 0
    mst: str = ""
    ten_cty: str = ""
    username: str = ""          # Thường = MST
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    # Password lưu trong keyring, KHÔNG lưu trong entity


# ══════════════════════════════════════════════════════════
# CẤU HÌNH CỘT (Column Config)
# ══════════════════════════════════════════════════════════

@dataclass
class ColumnConfig:
    """Cấu hình 1 cột trong bảng hiển thị.
    
    User tự chọn cột hiển thị, thứ tự, chiều rộng.
    Hỗ trợ cả cột Tầng 1 (fixed) và Tầng 2 (dynamic/extras).
    """
    column_key: str = ""        # Key nội bộ: 'so_hd', 'tong_tien', 'ext_BookingCode'
    display_name: str = ""      # Tên hiển thị: 'Số HĐ', 'Tổng tiền'
    table_name: str = ""        # 'summary' | 'detail'
    is_visible: bool = True     # User có muốn hiển thị?
    sort_order: int = 0         # Thứ tự (0 = đầu tiên)
    width: int = 120            # Chiều rộng (pixels)
    format_type: str = "text"   # 'text' | 'number' | 'currency' | 'date'
    is_dynamic: bool = False    # True = field từ Tầng 2 (extras)
    scope: str = ""             # Scope nếu dynamic: 'header', 'seller', 'item'...


# ══════════════════════════════════════════════════════════
# FIELD REGISTRY (Auto-Discovery)
# ══════════════════════════════════════════════════════════

@dataclass
class FieldRegistryEntry:
    """Một field đã được phát hiện tự động từ TTKhac."""
    id: int = 0
    scope: str = ""             # 'header' | 'seller' | 'buyer' | 'item' | 'payment' | 'invoice'
    field_key: str = ""         # Key gốc từ TTKhac (vd: 'BookingCode')
    display_name: str = ""      # Tên hiển thị (mặc định = field_key)
    format_type: str = "text"   # 'text' | 'number' | 'currency' | 'date'
    first_seen: str = ""        # Ngày phát hiện lần đầu
    vendor_hint: str = ""       # Vendor thường có field này
    seen_count: int = 1         # Số lần gặp


# ══════════════════════════════════════════════════════════
# KẾT QUẢ TRẢ VỀ (Result Types)
# ══════════════════════════════════════════════════════════

@dataclass
class CaptchaResult:
    """Kết quả lấy captcha."""
    image_bytes: bytes = b""
    captcha_key: str = ""
    content_type: str = ""    # "svg" | "png" — loại nội dung captcha
    success: bool = False
    error_msg: str = ""


@dataclass
class LoginResult:
    """Kết quả đăng nhập."""
    success: bool = False
    token: str = ""
    error_msg: str = ""


@dataclass
class InvoiceSummary:
    """Thông tin tóm tắt 1 HĐ từ API (trước khi tải XML)."""
    # Thông tin từ API response
    khhdon: str = ""            # Ký hiệu
    shdon: str = ""             # Số HĐ  
    ngay_lap: str = ""          # Ngày lập (tdlap)
    mst_nban: str = ""          # MST người bán
    ten_nban: str = ""          # Tên người bán
    mst_nmua: str = ""          # MST người mua
    ten_nmua: str = ""          # Tên người mua
    tong_tien_cthue: str = ""   # Tổng tiền chưa thuế
    tong_tien_thue: str = ""    # Tổng tiền thuế
    tong_thanh_toan: str = ""   # Tổng thanh toán
    trang_thai: str = ""        # Trạng thái xử lý (ttxly)
    trang_thai_label: str = ""  # Label hiển thị
    loai_hd: str = ""           # Loại ('purchase' | 'sold')
    raw_data: Dict = field(default_factory=dict)  # JSON gốc từ API


@dataclass
class QueryResult:
    """Kết quả tra cứu danh sách HĐ từ API."""
    invoices: List[InvoiceSummary] = field(default_factory=list)
    total: int = 0
    page_size: int = 50
    state: str = ""             # Cursor cho trang tiếp theo
    success: bool = False
    error_msg: str = ""


@dataclass
class DownloadResult:
    """Kết quả tải 1 file XML."""
    success: bool = False
    file_path: str = ""
    error_msg: str = ""


@dataclass
class BatchDownloadResult:
    """Kết quả tải nhiều file XML."""
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    results: List[DownloadResult] = field(default_factory=list)


@dataclass
class ExportResult:
    """Kết quả export Excel."""
    success: bool = False
    file_path: str = ""
    row_count: int = 0
    error_msg: str = ""


@dataclass
class UpdateCheckResult:
    """Kết quả kiểm tra Remote Config."""
    has_update: bool = False
    remote_version: str = ""
    local_version: str = ""
    remote_data: Dict = field(default_factory=dict)
    error_msg: str = ""
