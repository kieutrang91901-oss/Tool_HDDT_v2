"""
AccountService — Quản lý nhiều MST / tài khoản đăng nhập.

Kết hợp DBHandler (lưu MST, tên CTY) + CredentialStore (lưu password).
"""
from typing import List, Optional
from app.models.db_handler import DBHandler
from app.models.credential_store import CredentialStore
from app.models.entities import Account
from config.logger import get_logger

logger = get_logger(__name__)


class AccountService:
    """Quản lý tài khoản đăng nhập cổng thuế."""
    
    def __init__(self, db: DBHandler, credential_store: CredentialStore):
        self._db = db
        self._cred = credential_store
    
    # ═══════════════════════════════════════════════════════
    # CRUD
    # ═══════════════════════════════════════════════════════
    
    def get_all_accounts(self) -> List[Account]:
        """Lấy tất cả tài khoản."""
        return self._db.get_all_accounts()
    
    def get_account(self, mst: str) -> Optional[Account]:
        """Lấy thông tin 1 tài khoản."""
        return self._db.get_account(mst)
    
    def add_account(
        self,
        mst: str,
        password: str,
        ten_cty: str = "",
        username: str = "",
    ) -> bool:
        """Thêm tài khoản mới.
        
        Lưu MST + tên CTY vào DB, password vào keyring.
        """
        if not mst:
            logger.warning("Cannot add account: MST is empty")
            return False
        
        # Lưu vào DB
        success = self._db.add_account(mst, ten_cty, username or mst)
        if not success:
            return False
        
        # Lưu password vào keyring
        if password:
            self._cred.set_password(mst, password)
        
        logger.info(f"Account added: {mst} ({ten_cty})")
        return True
    
    def update_account(
        self,
        mst: str,
        password: Optional[str] = None,
        ten_cty: Optional[str] = None,
        username: Optional[str] = None,
    ) -> bool:
        """Cập nhật tài khoản.
        
        Chỉ cập nhật các field được truyền vào (không None).
        """
        kwargs = {}
        if ten_cty is not None:
            kwargs["ten_cty"] = ten_cty
        if username is not None:
            kwargs["username"] = username
        
        if kwargs:
            self._db.update_account(mst, **kwargs)
        
        # Cập nhật password nếu có
        if password is not None:
            self._cred.set_password(mst, password)
        
        logger.info(f"Account updated: {mst}")
        return True
    
    def delete_account(self, mst: str) -> bool:
        """Xóa tài khoản (DB + keyring)."""
        self._db.delete_account(mst)
        self._cred.delete_password(mst)
        logger.info(f"Account deleted: {mst}")
        return True
    
    # ═══════════════════════════════════════════════════════
    # PASSWORD
    # ═══════════════════════════════════════════════════════
    
    def get_password(self, mst: str) -> Optional[str]:
        """Đọc mật khẩu từ keyring."""
        return self._cred.get_password(mst)
    
    def has_password(self, mst: str) -> bool:
        """Kiểm tra MST đã lưu password chưa."""
        return self._cred.has_password(mst)
    
    # ═══════════════════════════════════════════════════════
    # ACTIVE ACCOUNT
    # ═══════════════════════════════════════════════════════
    
    def set_active(self, mst: str) -> bool:
        """Đặt tài khoản đang sử dụng."""
        # Tắt tất cả trước
        for acc in self.get_all_accounts():
            if acc.is_active and acc.mst != mst:
                self._db.update_account(acc.mst, is_active=False)
        
        # Bật tài khoản được chọn
        return self._db.update_account(mst, is_active=True)
    
    def get_active_account(self) -> Optional[Account]:
        """Lấy tài khoản đang hoạt động."""
        accounts = self.get_all_accounts()
        for acc in accounts:
            if acc.is_active:
                return acc
        # Fallback: trả về tài khoản đầu tiên
        return accounts[0] if accounts else None
