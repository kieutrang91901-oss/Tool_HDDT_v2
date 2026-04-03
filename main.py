"""
Tool Quản Lý Hóa Đơn Điện Tử v2
Entry point — Điểm khởi động duy nhất.
"""
import sys
import os

# Force UTF-8 output encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo project root nằm trong sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # Set CWD to project root

print("[HDDT] Starting application...")

from config.logger import setup_logging, get_logger
from config.settings import APP_NAME, APP_VERSION


def main():
    """Khởi động ứng dụng."""
    setup_logging()
    logger = get_logger(__name__)
    logger.info(f"{'='*60}")
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"{'='*60}")

    print("[HDDT] Loading UI...")
    from app.ui.main_window import MainWindow

    print("[HDDT] Creating window...")
    app = MainWindow()

    print("[HDDT] Window ready - showing now")
    app.deiconify()  # Đảm bảo window không bị iconify
    app.run()


if __name__ == "__main__":
    main()
