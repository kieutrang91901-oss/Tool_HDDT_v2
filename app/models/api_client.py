"""
API Client — Giao tiếp với cổng thuế hoadondientu.gdt.gov.vn.

Sử dụng httpx cho HTTP/2, session management, retry logic.

KHÔNG import bất kỳ thư viện UI nào.
"""
import httpx
import json
from typing import Optional, Dict, Any
from config.api_config import GDT_API_Config as API
from config.settings import API_TIMEOUT, API_RETRY_COUNT
from config.logger import get_logger
from app.models.entities import CaptchaResult, LoginResult

logger = get_logger(__name__)


class APIClient:
    """HTTP Client cho cổng thuế điện tử."""
    
    def __init__(self):
        self._client: Optional[httpx.Client] = None
        self._token: str = ""
    
    @property
    def client(self) -> httpx.Client:
        """Lazy-init httpx Client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=API_TIMEOUT,
                verify=False,  # Cổng thuế dùng self-signed cert
                follow_redirects=True,
            )
        return self._client
    
    @property
    def is_authenticated(self) -> bool:
        """Kiểm tra đã có token chưa."""
        return bool(self._token)
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Headers có kèm token xác thực."""
        headers = dict(API.DEFAULT_HEADERS)
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers
    
    # ═══════════════════════════════════════════════════════
    # XÁC THỰC (Auth)
    # ═══════════════════════════════════════════════════════
    
    def get_captcha(self) -> CaptchaResult:
        """Lấy captcha từ cổng thuế.
        
        API trả về: {"key": "...", "content": "<svg ...>...</svg>"}
        Content là SVG markup.
        
        Returns:
            CaptchaResult với image_bytes (SVG as bytes) + captcha_key.
        """
        result = CaptchaResult()
        try:
            url = API.get_url(API.EP_CAPTCHA)
            resp = self.client.get(url, headers=API.DEFAULT_HEADERS)
            
            if resp.status_code == 200:
                data = resp.json()
                result.captcha_key = data.get("key", "")
                
                content = data.get("content", "")
                if content:
                    # Content is SVG markup — store as bytes
                    if content.strip().startswith("<svg"):
                        result.image_bytes = content.encode("utf-8")
                        result.content_type = "svg"
                    else:
                        # Fallback: maybe base64
                        import base64
                        # Strip data URI prefix if present
                        if "base64," in content:
                            content = content.split("base64,", 1)[1]
                        result.image_bytes = base64.b64decode(content)
                        result.content_type = "png"
                
                result.success = True
                logger.info("Captcha fetched successfully")
            else:
                result.error_msg = f"HTTP {resp.status_code}"
                logger.error(f"Captcha fetch failed: HTTP {resp.status_code}")
        
        except Exception as e:
            result.error_msg = str(e)
            logger.error(f"Captcha fetch error: {e}")
        
        return result
    
    def login(
        self, mst: str, password: str, 
        captcha_text: str, captcha_key: str
    ) -> LoginResult:
        """Đăng nhập cổng thuế.
        
        Returns:
            LoginResult với token nếu thành công.
        """
        result = LoginResult()
        try:
            url = API.get_url(API.EP_LOGIN)
            payload = {
                "username": mst,
                "password": password,
                "cvalue": captcha_text,
                "ckey": captcha_key,
            }
            
            resp = self.client.post(
                url,
                json=payload,
                headers=API.LOGIN_HEADERS,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token", "")
                if token:
                    self._token = token
                    result.success = True
                    result.token = token
                    logger.info(f"Login successful for MST: {mst}")
                else:
                    result.error_msg = data.get("message", "Đăng nhập thất bại")
                    logger.warning(f"Login failed for {mst}: {result.error_msg}")
            else:
                result.error_msg = f"HTTP {resp.status_code}"
                logger.error(f"Login failed: HTTP {resp.status_code}")
        
        except Exception as e:
            result.error_msg = str(e)
            logger.error(f"Login error for {mst}: {e}")
        
        return result
    
    def logout(self) -> None:
        """Xóa session."""
        self._token = ""
        logger.info("Logged out")
    
    # ═══════════════════════════════════════════════════════
    # TRA CỨU HÓA ĐƠN
    # ═══════════════════════════════════════════════════════
    
    def query_invoices(
        self,
        loai: str,              # 'purchase' | 'sold'
        tu_ngay: str,           # DD/MM/YYYYTHH:MM:SS
        den_ngay: str,          # DD/MM/YYYYTHH:MM:SS
        trang_thai: str = "",   # ttxly filter (5, 6, 8)
        page: int = 1,
        page_size: int = 50,
        is_sco: bool = False,   # Máy tính tiền
    ) -> Dict[str, Any]:
        """Tra cứu danh sách hóa đơn từ API.
        
        Returns:
            Dict: {"datas": [...], "total": N, ...} hoặc {"error": "..."}
        """
        try:
            # Xây dựng endpoint
            ep = API.EP_INVOICE_SOLD if loai == "sold" else API.EP_INVOICE_PURCHASE
            url = API.get_invoice_url(ep, is_sco=is_sco)
            
            # Xây dựng search params
            search_parts = [
                f"tdlap=ge={tu_ngay}",
                f"tdlap=le={den_ngay}",
            ]
            if trang_thai:
                search_parts.append(f"ttxly=={trang_thai}")
            
            params = {
                "sort": "tdlap:desc",
                "size": str(page_size),
                "search": ";".join(search_parts),
            }
            
            if page > 1:
                params["from"] = str((page - 1) * page_size)
            
            resp = self.client.get(
                url,
                params=params,
                headers=self._get_auth_headers(),
            )
            
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                logger.warning("Session expired")
                self._token = ""
                return {"error": "Session hết hạn. Vui lòng đăng nhập lại."}
            else:
                return {"error": f"HTTP {resp.status_code}"}
        
        except Exception as e:
            logger.error(f"Query invoices error: {e}")
            return {"error": str(e)}
    
    def download_xml(self, nbmst: str, khhdon: str, shdon: str, khmshdon: str = "1") -> Optional[bytes]:
        """Tải file XML hóa đơn.
        
        Args:
            nbmst: MST người bán
            khhdon: Ký hiệu hóa đơn
            shdon: Số hóa đơn
            khmshdon: Mẫu số HĐ (thường = "1")
        
        Returns:
            bytes: Nội dung ZIP file, hoặc None nếu lỗi.
        """
        try:
            url = API.get_invoice_url(API.EP_EXPORT_XML)
            payload = {
                "nbmst": nbmst,
                "khhdon": khhdon,
                "shdon": shdon,
                "khmshdon": khmshdon,
            }
            
            resp = self.client.post(
                url,
                json=payload,
                headers=self._get_auth_headers(),
            )
            
            if resp.status_code == 200:
                logger.info(f"Downloaded XML: {khhdon}-{shdon}")
                return resp.content
            else:
                logger.error(f"Download failed for {khhdon}-{shdon}: HTTP {resp.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Download error for {khhdon}-{shdon}: {e}")
            return None
    
    def close(self) -> None:
        """Đóng HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()
            logger.info("API Client closed")
