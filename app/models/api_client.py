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
            
            logger.info(f"Login request: URL={url}, MST={mst}, ckey={captcha_key[:20] if captcha_key else 'EMPTY'}...")
            
            resp = self.client.post(
                url,
                json=payload,
                headers=API.LOGIN_HEADERS,
            )
            
            logger.info(f"Login response: HTTP {resp.status_code}")
            
            # Debug: log response body (truncated for security)
            try:
                resp_text = resp.text[:500]
                logger.debug(f"Login response body: {resp_text}")
            except Exception:
                pass
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Cổng thuế có thể trả token ở nhiều vị trí khác nhau
                token = (
                    data.get("token", "")
                    or data.get("access_token", "")
                    or data.get("Token", "")
                )
                
                if token:
                    self._token = token
                    result.success = True
                    result.token = token
                    logger.info(f"Login successful for MST: {mst}, token_len={len(token)}")
                else:
                    # Không có token — kiểm tra message lỗi
                    msg = (
                        data.get("message", "")
                        or data.get("msg", "")
                        or data.get("error", "")
                        or "Đăng nhập thất bại — không nhận được token"
                    )
                    result.error_msg = msg
                    logger.warning(f"Login no token for {mst}: response_keys={list(data.keys())}, message={msg}")
            else:
                # HTTP error — cố parse JSON body để lấy message
                try:
                    err_data = resp.json()
                    result.error_msg = (
                        err_data.get("message", "")
                        or err_data.get("msg", "")
                        or f"HTTP {resp.status_code}"
                    )
                except Exception:
                    result.error_msg = f"HTTP {resp.status_code}"
                logger.error(f"Login failed: HTTP {resp.status_code}, error={result.error_msg}")
        
        except Exception as e:
            result.error_msg = str(e)
            logger.error(f"Login error for {mst}: {e}", exc_info=True)
        
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
        page_size: int = 50,
        is_sco: bool = False,   # Máy tính tiền
        state: str = "",        # Cursor pagination (từ response trước)
    ) -> Dict[str, Any]:
        """Tra cứu danh sách hóa đơn từ API.
        
        API dùng cursor pagination: response chứa 'state',
        truyền lại 'state' để lấy trang tiếp theo.
        
        Returns:
            Dict: {"datas": [...], "total": N, "state": "..."} hoặc {"error": "..."}
        """
        try:
            ep = API.EP_INVOICE_SOLD if loai == "sold" else API.EP_INVOICE_PURCHASE
            url = API.get_invoice_url(ep, is_sco=is_sco)
            
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
            
            # Cursor-based pagination
            if state:
                params["state"] = state
            
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
    
    def get_invoice_detail(
        self,
        nbmst: str,
        khhdon: str,
        shdon: str,
        khmshdon: str = "1",
        is_sco: bool = False,
    ) -> Dict[str, Any]:
        """Lấy chi tiết 1 hóa đơn từ API.
        
        Endpoint:
          - Normal: /query/invoices/detail?nbmst=...&khhdon=...&shdon=...&khmshdon=...
          - SCO:    /sco-query/invoices/detail?...
        
        Returns:
            Dict: JSON response hoặc {"error": "..."}
        """
        try:
            url = API.get_invoice_url(API.EP_INVOICE_DETAIL, is_sco=is_sco)
            params = {
                "nbmst": nbmst,
                "khhdon": khhdon,
                "shdon": shdon,
                "khmshdon": khmshdon,
            }
            
            resp = self.client.get(
                url,
                params=params,
                headers=self._get_auth_headers(),
            )
            
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"Invoice detail OK: {khhdon}-{shdon}")
                return data
            elif resp.status_code == 401:
                logger.warning("Session expired")
                self._token = ""
                return {"error": "Session hết hạn. Vui lòng đăng nhập lại."}
            else:
                logger.warning(f"Invoice detail HTTP {resp.status_code}: {khhdon}-{shdon}")
                return {"error": f"HTTP {resp.status_code}"}
        
        except Exception as e:
            logger.error(f"Invoice detail error: {e}")
            return {"error": str(e)}
    
    def download_xml(
        self, nbmst: str, khhdon: str, shdon: str,
        khmshdon: str = "1", is_sco: bool = False,
    ) -> Optional[bytes]:
        """Tải file XML hóa đơn bằng GET + params.
        
        Endpoint:
          - Bình thường: /query/invoices/export-xml?nbmst=...&khhdon=...&shdon=...&khmshdon=...
          - MTT/POS:     /sco-query/invoices/export-xml?...
        
        Args:
            nbmst: MST người bán
            khhdon: Ký hiệu hóa đơn
            shdon: Số hóa đơn
            khmshdon: Ký hiệu mẫu số HĐ (thường = "1")
            is_sco: True nếu HĐ máy tính tiền
        
        Returns:
            bytes: Nội dung XML/ZIP file, hoặc None nếu lỗi.
        """
        import time
        
        max_retries = 3
        base_delay = 1.5  # Seconds
        
        url = API.get_invoice_url(API.EP_EXPORT_XML, is_sco=is_sco)
        params = {
            "nbmst": nbmst,
            "khhdon": khhdon,
            "shdon": shdon,
            "khmshdon": khmshdon,
        }
        
        # Headers: auth + Accept: application/xml
        headers = dict(API.EXPORT_XML_HEADERS)
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        for attempt in range(max_retries):
            try:
                resp = self.client.get(
                    url,
                    params=params,
                    headers=headers,
                )
                
                if resp.status_code == 200:
                    if len(resp.content) > 0:
                        logger.info(f"Downloaded XML: {khhdon}-{shdon} ({len(resp.content)} bytes)")
                        return resp.content
                    else:
                        logger.warning(f"Download empty response for {khhdon}-{shdon}")
                        return None
                
                elif resp.status_code == 429:
                    # Rate limited — wait and retry
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limited (429) for {khhdon}-{shdon}, "
                        f"retry {attempt+1}/{max_retries} after {delay:.1f}s"
                    )
                    time.sleep(delay)
                    continue
                
                elif resp.status_code == 500:
                    delay = base_delay * (attempt + 1)
                    logger.warning(
                        f"Server error (500) for {khhdon}-{shdon}, "
                        f"retry {attempt+1}/{max_retries} after {delay:.1f}s"
                    )
                    try:
                        logger.debug(f"500 response body: {resp.text[:300]}")
                    except Exception:
                        pass
                    time.sleep(delay)
                    continue
                
                elif resp.status_code == 401:
                    logger.error(f"Download auth failed (401) for {khhdon}-{shdon}")
                    self._token = ""
                    return None
                
                else:
                    logger.error(f"Download failed for {khhdon}-{shdon}: HTTP {resp.status_code}")
                    try:
                        logger.debug(f"Response: {resp.text[:200]}")
                    except Exception:
                        pass
                    return None
            
            except Exception as e:
                logger.error(f"Download error for {khhdon}-{shdon}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay)
                    continue
                return None
        
        logger.error(f"Download failed after {max_retries} retries: {khhdon}-{shdon}")
        return None
    
    def get_invoice_detail(
        self,
        nbmst: str,
        khhdon: str,
        shdon: str,
        khmshdon: str = "1",
        is_sco: bool = False,
    ) -> Dict[str, Any]:
        """Lấy chi tiết 1 hóa đơn (bao gồm hdhhdvu items).
        
        Args:
            nbmst: MST người bán
            khhdon: Ký hiệu HĐ
            shdon: Số HĐ
            khmshdon: Ký hiệu mẫu số HĐ
            is_sco: True nếu HĐ máy tính tiền
            
        Returns:
            Dict: full invoice data including hdhhdvu[], or {"error": "..."}
        """
        try:
            url = API.get_invoice_url(API.EP_INVOICE_DETAIL, is_sco=is_sco)
            params = {
                "nbmst": nbmst,
                "khhdon": khhdon,
                "shdon": str(shdon),
                "khmshdon": str(khmshdon),
            }
            
            resp = self.client.get(
                url,
                params=params,
                headers=self._get_auth_headers(),
            )
            
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                self._token = ""
                return {"error": "Session hết hạn"}
            else:
                return {"error": f"HTTP {resp.status_code}"}
        
        except Exception as e:
            logger.error(f"Invoice detail error {khhdon}-{shdon}: {e}")
            return {"error": str(e)}
    
    def export_excel(
        self,
        tu_ngay: str,
        den_ngay: str,
        is_sco: bool = False,
    ) -> Optional[bytes]:
        """Tải bảng kê hóa đơn Excel từ cổng thuế.
        
        URL mẫu: /query/invoices/export-excel?sort=tdlap:desc&search=tdlap=ge=...;tdlap=le=...
        
        Args:
            tu_ngay: Từ ngày (DD/MM/YYYYTHH:MM:SS)
            den_ngay: Đến ngày (DD/MM/YYYYTHH:MM:SS)
            is_sco: True nếu tải HĐ máy tính tiền
            
        Returns:
            bytes: Nội dung file Excel, hoặc None nếu lỗi.
        """
        try:
            url = API.get_invoice_url(API.EP_EXPORT_EXCEL, is_sco=is_sco)
            params = {
                "sort": "tdlap:desc",
                "search": f"tdlap=ge={tu_ngay};tdlap=le={den_ngay}",
            }
            
            headers = dict(API.DEFAULT_HEADERS)
            headers["Accept"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*"
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            
            resp = self.client.get(url, params=params, headers=headers, timeout=60.0)
            
            if resp.status_code == 200 and len(resp.content) > 0:
                logger.info(
                    f"Export Excel {'SCO ' if is_sco else ''}OK: "
                    f"{len(resp.content)} bytes"
                )
                return resp.content
            else:
                logger.warning(f"Export Excel failed: HTTP {resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Export Excel error: {e}")
            return None
    
    def close(self) -> None:
        """Đóng HTTP client."""
        if self._client and not self._client.is_closed:
            self._client.close()
            logger.info("API Client closed")
