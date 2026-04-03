"""
Credential Store — Lưu trữ mật khẩu an toàn qua Windows Credential Locker.

Sử dụng thư viện keyring để mã hóa mật khẩu bởi OS.
Password KHÔNG BAO GIỜ lưu trong DB hoặc file config.
"""
from typing import Optional
from config.settings import KEYRING_SERVICE_NAME
from config.logger import get_logger

logger = get_logger(__name__)

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring not installed. Passwords will NOT be stored securely.")


class CredentialStore:
    """Wrapper quản lý mật khẩu qua Windows Credential Locker."""
    
    def __init__(self, service_name: str = KEYRING_SERVICE_NAME):
        self.service_name = service_name
    
    def set_password(self, mst: str, password: str) -> bool:
        """Lưu mật khẩu cho 1 MST."""
        if not KEYRING_AVAILABLE:
            logger.error("keyring not available. Cannot store password.")
            return False
        try:
            keyring.set_password(self.service_name, mst, password)
            logger.info(f"Password stored for MST: {mst}")
            return True
        except Exception as e:
            logger.error(f"Failed to store password for {mst}: {e}")
            return False
    
    def get_password(self, mst: str) -> Optional[str]:
        """Đọc mật khẩu đã lưu cho 1 MST."""
        if not KEYRING_AVAILABLE:
            logger.error("keyring not available. Cannot retrieve password.")
            return None
        try:
            password = keyring.get_password(self.service_name, mst)
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve password for {mst}: {e}")
            return None
    
    def delete_password(self, mst: str) -> bool:
        """Xóa mật khẩu đã lưu."""
        if not KEYRING_AVAILABLE:
            return False
        try:
            keyring.delete_password(self.service_name, mst)
            logger.info(f"Password deleted for MST: {mst}")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"No password found to delete for MST: {mst}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete password for {mst}: {e}")
            return False
    
    def has_password(self, mst: str) -> bool:
        """Kiểm tra MST đã có mật khẩu lưu hay chưa."""
        return self.get_password(mst) is not None
    
    @staticmethod
    def is_available() -> bool:
        """Kiểm tra keyring có sẵn trên hệ thống không."""
        return KEYRING_AVAILABLE
