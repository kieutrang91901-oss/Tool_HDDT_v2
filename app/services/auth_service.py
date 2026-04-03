"""
AuthService — Quản lý đăng nhập / session với cổng thuế.

Kết hợp APIClient + CredentialStore để xác thực.
Chạy trên thread riêng để không block UI.
"""
from typing import Optional, Callable
from app.models.api_client import APIClient
from app.models.credential_store import CredentialStore
from app.models.entities import CaptchaResult, LoginResult
from config.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Quản lý xác thực với cổng thuế."""
    
    def __init__(self, api_client: APIClient, credential_store: CredentialStore):
        self._api = api_client
        self._cred = credential_store
        self._current_mst: str = ""
        self._is_logged_in: bool = False
    
    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in and self._api.is_authenticated
    
    @property
    def current_mst(self) -> str:
        return self._current_mst
    
    # ═══════════════════════════════════════════════════════
    # CAPTCHA
    # ═══════════════════════════════════════════════════════
    
    def get_captcha(self) -> CaptchaResult:
        """Lấy ảnh captcha từ cổng thuế.
        
        Returns:
            CaptchaResult với image_bytes + captcha_key.
        """
        try:
            result = self._api.get_captcha()
            if not result.success:
                logger.warning(f"Captcha fetch failed: {result.error_msg}")
            return result
        except Exception as e:
            logger.error(f"Captcha error: {e}")
            return CaptchaResult(error_msg=str(e))
    
    # ═══════════════════════════════════════════════════════
    # LOGIN / LOGOUT
    # ═══════════════════════════════════════════════════════
    
    def login(
        self,
        mst: str,
        password: str,
        captcha_text: str,
        captcha_key: str,
    ) -> LoginResult:
        """Đăng nhập cổng thuế.
        
        Args:
            mst: Mã số thuế
            password: Mật khẩu
            captcha_text: Text người dùng nhập từ ảnh captcha
            captcha_key: Key captcha (từ get_captcha)
        
        Returns:
            LoginResult
        """
        try:
            # Validate input
            if not mst or not password:
                return LoginResult(error_msg="MST và mật khẩu không được để trống")
            if not captcha_text:
                return LoginResult(error_msg="Vui lòng nhập mã captcha")
            
            result = self._api.login(mst, password, captcha_text, captcha_key)
            
            if result.success:
                self._current_mst = mst
                self._is_logged_in = True
                logger.info(f"Auth: Logged in as {mst}")
            else:
                self._is_logged_in = False
                logger.warning(f"Auth: Login failed for {mst}: {result.error_msg}")
            
            return result
            
        except Exception as e:
            logger.error(f"Auth: Login error: {e}")
            return LoginResult(error_msg=str(e))
    
    def login_with_saved_password(
        self,
        mst: str,
        captcha_text: str,
        captcha_key: str,
    ) -> LoginResult:
        """Đăng nhập bằng password đã lưu trong keyring."""
        password = self._cred.get_password(mst)
        if not password:
            return LoginResult(error_msg=f"Không tìm thấy mật khẩu cho MST: {mst}")
        return self.login(mst, password, captcha_text, captcha_key)
    
    def logout(self) -> None:
        """Đăng xuất."""
        self._api.logout()
        self._current_mst = ""
        self._is_logged_in = False
        logger.info("Auth: Logged out")
    
    # ═══════════════════════════════════════════════════════
    # SESSION CHECK
    # ═══════════════════════════════════════════════════════
    
    def is_session_valid(self) -> bool:
        """Kiểm tra session còn hiệu lực không.
        
        Thực hiện bằng cách thử gọi 1 API đơn giản.
        """
        if not self._is_logged_in:
            return False
        return self._api.is_authenticated
