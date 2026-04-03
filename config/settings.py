"""
Cấu hình trung tâm ứng dụng Tool HDDT v2.
Tất cả hằng số, đường dẫn, thông tin phiên bản đều tập trung tại đây.
"""
import os
import sys

# ═══════════════════════════════════════════════════════
# THÔNG TIN ỨNG DỤNG
# ═══════════════════════════════════════════════════════
APP_NAME = "Tool Quản Lý Hóa Đơn Điện Tử"
APP_NAME_SHORT = "Tool HDDT"
APP_VERSION = "2.0.0"
APP_AUTHOR = "HDDT Team"

# ═══════════════════════════════════════════════════════
# ĐƯỜNG DẪN
# ═══════════════════════════════════════════════════════

def _get_base_dir() -> str:
    """Lấy thư mục gốc của ứng dụng (hỗ trợ cả dev và PyInstaller)."""
    if getattr(sys, 'frozen', False):
        # Đang chạy từ file EXE (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Đang chạy từ source code
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = _get_base_dir()
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# Database
DB_PATH = os.path.join(DATA_DIR, "app.db")

# Logs
LOG_FILE = os.path.join(LOGS_DIR, "app.log")
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3

# ═══════════════════════════════════════════════════════
# AUTO-CREATE DIRECTORIES
# ═══════════════════════════════════════════════════════
for _dir in [DATA_DIR, LOGS_DIR]:
    os.makedirs(_dir, exist_ok=True)

# ═══════════════════════════════════════════════════════
# HIỆU NĂNG
# ═══════════════════════════════════════════════════════
PARSER_MAX_WORKERS = 8          # Số thread tối đa cho batch parse XML
API_TIMEOUT = 30                # Timeout cho HTTP requests (giây)
API_RETRY_COUNT = 3             # Số lần retry khi API lỗi
DEFAULT_PAGE_SIZE = 50          # Số dòng mặc định mỗi trang
TABLE_VIRTUAL_ROWS = 10_000    # Ngưỡng bật virtual scrolling cho tksheet

# ═══════════════════════════════════════════════════════
# KEYRING
# ═══════════════════════════════════════════════════════
KEYRING_SERVICE_NAME = "ToolHDDT_v2"  # Service name trong Windows Credential Locker

# ═══════════════════════════════════════════════════════
# REMOTE CONFIG
# ═══════════════════════════════════════════════════════
REMOTE_CONFIG_URL = "https://raw.githubusercontent.com/hddt-tool/config/main/remote_config.json"
REMOTE_CONFIG_CHECK_INTERVAL = 3600  # Kiểm tra mỗi 1 giờ (giây)
