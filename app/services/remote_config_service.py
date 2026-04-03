"""
RemoteConfigService — Tự động cập nhật API endpoints từ server/GitHub.

Đảm bảo N users luôn dùng endpoint mới nhất khi Tổng Cục Thuế thay đổi.
- Fetch remote config khi app khởi động (background, không block UI)
- So sánh version: remote > local → cập nhật
- Fallback: không có mạng → dùng config local đã cache trong SQLite

Remote Config URL: GitHub Raw hoặc server riêng.
"""
import json
from typing import Optional, Dict
import httpx

from app.models.db_handler import DBHandler
from app.models.entities import UpdateCheckResult
from config.api_config import GDT_API_Config as API
from config.settings import REMOTE_CONFIG_URL
from config.logger import get_logger

logger = get_logger(__name__)


class RemoteConfigService:
    """Tự động cập nhật API config từ remote server."""
    
    def __init__(self, db: DBHandler):
        self._db = db
    
    # ═══════════════════════════════════════════════════════
    # CHECK FOR UPDATES
    # ═══════════════════════════════════════════════════════
    
    def check_for_updates(self) -> UpdateCheckResult:
        """Kiểm tra remote config có bản mới không.
        
        Gọi khi app khởi động. Không block UI (gọi trong thread).
        
        Returns:
            UpdateCheckResult
        """
        result = UpdateCheckResult(local_version=API.VERSION)
        
        try:
            # Fetch remote config
            remote_data = self._fetch_remote_config()
            if remote_data is None:
                result.error_msg = "Không thể kết nối remote config"
                # Cập nhật thời gian check
                self._db.update_remote_check_time()
                return result
            
            remote_version = remote_data.get("version", "0.0.0")
            result.remote_version = remote_version
            result.remote_data = remote_data
            
            # So sánh version
            if self._compare_versions(remote_version, API.VERSION) > 0:
                result.has_update = True
                logger.info(
                    f"Remote config update available: {API.VERSION} → {remote_version}"
                )
            else:
                logger.info(f"Remote config up to date: {API.VERSION}")
            
            self._db.update_remote_check_time()
            
        except Exception as e:
            result.error_msg = str(e)
            logger.error(f"Remote config check error: {e}")
        
        return result
    
    # ═══════════════════════════════════════════════════════
    # APPLY UPDATE
    # ═══════════════════════════════════════════════════════
    
    def apply_update(self, remote_data: Dict) -> bool:
        """Áp dụng remote config mới.
        
        1. Cập nhật GDT_API_Config runtime
        2. Lưu vào DB (cache cho lần sau)
        """
        try:
            version = remote_data.get("version", "")
            api_config = remote_data.get("api_config", {})
            
            if not api_config:
                logger.warning("Remote config has no api_config data")
                return False
            
            # Cập nhật runtime
            API.update_from_dict(api_config)
            API.VERSION = version
            
            # Lưu vào DB
            self._db.save_remote_config(
                key="api_config",
                version=version,
                data=remote_data,
            )
            
            changelog = remote_data.get("changelog", "")
            logger.info(
                f"Remote config applied: v{version}"
                f"{f' — {changelog}' if changelog else ''}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply remote config: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════
    # AUTO-UPDATE (check + apply one-shot)
    # ═══════════════════════════════════════════════════════
    
    def auto_update(self) -> Optional[str]:
        """Kiểm tra và tự động cập nhật nếu có phiên bản mới.
        
        Gọi khi app khởi động trong background thread.
        
        Returns:
            Changelog string nếu đã cập nhật, None nếu không có update.
        """
        # Bước 1: Load cached config từ DB trước (fallback)
        self._load_cached_config()
        
        # Bước 2: Check remote
        result = self.check_for_updates()
        
        if result.has_update and result.remote_data:
            success = self.apply_update(result.remote_data)
            if success:
                return result.remote_data.get("changelog", f"Cập nhật v{result.remote_version}")
        
        return None
    
    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════
    
    def _fetch_remote_config(self) -> Optional[Dict]:
        """Fetch remote config từ URL."""
        try:
            resp = httpx.get(
                REMOTE_CONFIG_URL,
                timeout=10,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Remote config HTTP {resp.status_code}")
                return None
        except httpx.TimeoutException:
            logger.warning("Remote config timeout")
            return None
        except Exception as e:
            logger.warning(f"Remote config fetch error: {e}")
            return None
    
    def _load_cached_config(self) -> None:
        """Load config đã cache từ DB (dùng khi không có mạng)."""
        cached = self._db.get_remote_config("api_config")
        if cached and cached.get("data"):
            api_config = cached["data"].get("api_config", {})
            if api_config:
                API.update_from_dict(api_config)
                API.VERSION = cached.get("version", API.VERSION)
                logger.info(f"Loaded cached remote config v{API.VERSION}")
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """So sánh 2 phiên bản (semantic versioning).
        
        Returns:
            > 0 nếu v1 > v2
            = 0 nếu v1 == v2
            < 0 nếu v1 < v2
        """
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                if p1 != p2:
                    return p1 - p2
            return 0
        except Exception:
            return 0
    
    def get_current_config(self) -> Dict:
        """Lấy config đang sử dụng."""
        return API.to_dict()
    
    def get_remote_url(self) -> str:
        """Lấy URL remote config."""
        return REMOTE_CONFIG_URL
