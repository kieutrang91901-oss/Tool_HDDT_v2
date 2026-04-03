"""
Cấu hình Logging trung tâm cho Tool HDDT v2.
Ghi log ra file (rotating) + console với format chuẩn.
"""
import logging
import logging.handlers
from config.settings import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOGS_DIR
import os

# Đảm bảo thư mục logs tồn tại
os.makedirs(LOGS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════
# FORMAT
# ═══════════════════════════════════════════════════════
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ═══════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════

def setup_logging(level: int = logging.INFO) -> None:
    """Khởi tạo hệ thống logging cho toàn bộ ứng dụng.
    
    Gọi 1 lần duy nhất khi app khởi động (trong main.py).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Xóa handlers cũ (tránh duplicate khi gọi lại)
    root_logger.handlers.clear()
    
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Handler 1: Ghi ra file (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Handler 2: Hiển thị trên console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Giảm noise từ thư viện bên ngoài
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Tạo logger cho một module cụ thể.
    
    Usage:
        from config.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Đã đăng nhập thành công")
    """
    return logging.getLogger(name)
