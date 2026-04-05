"""
Cấu hình API Tổng Cục Thuế (hoadondientu.gdt.gov.vn).

⚠️ File này là cấu hình LOCAL mặc định.
   Khi Remote Config có bản mới hơn, các giá trị sẽ được override tại runtime.
   Xem: app/services/remote_config_service.py
"""


class GDT_API_Config:
    """
    Cấu hình tập trung toàn bộ Endpoint, URL, Header cho cổng Thuế điện tử.
    
    VERSION: Dùng để so sánh với Remote Config.
    Khi TCT thay đổi link → cập nhật Remote Config → tất cả users tự động nhận.
    """
    
    # Phiên bản config (để so sánh với remote)
    VERSION = "1.0.0"
    
    # ═══════════════════════════════════════════════════════
    # 1. BASE URL
    # ═══════════════════════════════════════════════════════
    BASE_URL = "https://hoadondientu.gdt.gov.vn:30000"
    
    # ═══════════════════════════════════════════════════════
    # 2. HEADERS
    # ═══════════════════════════════════════════════════════
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
    }

    LOGIN_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/105.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept-Encoding": "gzip",
    }

    # Headers cho export XML (tải hóa đơn)
    EXPORT_XML_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/xml",
    }
    
    # ═══════════════════════════════════════════════════════
    # 3. ENDPOINTS XÁC THỰC (Auth)
    # ═══════════════════════════════════════════════════════
    EP_CAPTCHA = "/captcha"
    EP_LOGIN = "/security-taxpayer/authenticate"
    
    # ═══════════════════════════════════════════════════════
    # 4. PREFIX PHÂN LOẠI HÓA ĐƠN
    # ═══════════════════════════════════════════════════════
    # Hóa đơn bình thường: /query
    # Hóa đơn máy tính tiền (MTT/POS): /sco-query
    PREFIX_NORMAL = "query"
    PREFIX_SCO = "sco-query"
    
    # ═══════════════════════════════════════════════════════
    # 5. ENDPOINTS XỬ LÝ HÓA ĐƠN (nối sau prefix)
    # ═══════════════════════════════════════════════════════
    EP_INVOICE_PURCHASE = "/invoices/purchase"
    EP_INVOICE_SOLD = "/invoices/sold"
    EP_INVOICE_DETAIL = "/invoices/detail"
    EP_EXPORT_XML = "/invoices/export-xml"
    EP_EXPORT_EXCEL = "/invoices/export-excel"
    
    # ═══════════════════════════════════════════════════════
    # 6. TRẠNG THÁI XỬ LÝ (ttxly) — Dùng cho bộ lọc
    # ═══════════════════════════════════════════════════════
    TRANG_THAI = {
        "5": "Đã cấp mã",
        "6": "Cục thuế đã không cấp mã",
        "8": "CQT đã nhận HĐ có mã từ MTT",
    }
    
    # ═══════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════
    
    @classmethod
    def get_url(cls, endpoint: str) -> str:
        """Lấy Full URL cho các Endpoint tĩnh (Auth, etc.)."""
        return f"{cls.BASE_URL}{endpoint}"
    
    @classmethod
    def get_invoice_url(cls, endpoint: str, is_sco: bool = False) -> str:
        """Lấy Full URL có Prefix (Thường vs MTT)."""
        prefix = cls.PREFIX_SCO if is_sco else cls.PREFIX_NORMAL
        return f"{cls.BASE_URL}/{prefix}{endpoint}"
    
    @classmethod
    def to_dict(cls) -> dict:
        """Export toàn bộ config thành dict (để so sánh với remote)."""
        return {
            "VERSION": cls.VERSION,
            "BASE_URL": cls.BASE_URL,
            "EP_CAPTCHA": cls.EP_CAPTCHA,
            "EP_LOGIN": cls.EP_LOGIN,
            "PREFIX_NORMAL": cls.PREFIX_NORMAL,
            "PREFIX_SCO": cls.PREFIX_SCO,
            "EP_INVOICE_PURCHASE": cls.EP_INVOICE_PURCHASE,
            "EP_INVOICE_SOLD": cls.EP_INVOICE_SOLD,
            "EP_INVOICE_DETAIL": cls.EP_INVOICE_DETAIL,
            "EP_EXPORT_XML": cls.EP_EXPORT_XML,
        }
    
    @classmethod
    def update_from_dict(cls, data: dict) -> None:
        """Cập nhật config từ dict (nhận từ Remote Config)."""
        for key, value in data.items():
            if hasattr(cls, key) and key != "to_dict" and key != "update_from_dict":
                setattr(cls, key, value)
