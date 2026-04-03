class GDT_API_Config:
    """
    Cấu hình tập trung toàn bộ Endpoint, URL, Header cho hệ thống Giao tiếp Thuế.
    Bất kỳ thay đổi link nào sau này đều chỉ cần cập nhật tại file này.
    """
    
    # 1. BASE URL Của Tổng Cục Thuế
    BASE_URL = "https://hoadondientu.gdt.gov.vn:30000"
    
    # 2. Các Headers mặc định thường xuyên sử dụng
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8"
    }

    # Header tĩnh đòi hỏi chính xác khi xác thực đăng nhập
    LOGIN_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept-Encoding": "gzip"
    }
    
    # 3. Các Endpoints Xác cực (Auth)
    EP_CAPTCHA = "/captcha"
    EP_LOGIN = "/security-taxpayer/authenticate"
    
    # 4. Tiền tố phân loại hóa đơn (Prefix)
    # Hóa đơn bình thường: /query
    # Hóa đơn máy tính tiền (MTT) POS: /sco-query
    PREFIX_NORMAL = "query"
    PREFIX_SCO = "sco-query"
    
    # 5. Các Endpoints Xử lý Hóa đơn (Sẽ nối sau Prefix)
    EP_INVOICE_PURCHASE = "/invoices/purchase"
    EP_INVOICE_SOLD = "/invoices/sold"
    EP_INVOICE_DETAIL = "/invoices/detail"
    EP_EXPORT_XML = "/invoices/export-xml"
    
    @classmethod
    def get_url(cls, endpoint):
        """Hàm hỗ trợ lấy Full URL cho các Endpoint tĩnh không có Prefix"""
        return f"{cls.BASE_URL}{endpoint}"
        
    @classmethod
    def get_invoice_url(cls, endpoint, is_sco=False):
        """Hàm hỗ trợ lấy Full URL có Prefix (Thường vs MTT)"""
        prefix = cls.PREFIX_SCO if is_sco else cls.PREFIX_NORMAL
        return f"{cls.BASE_URL}/{prefix}{endpoint}"
