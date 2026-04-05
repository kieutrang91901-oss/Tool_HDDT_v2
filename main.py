"""Tool Quản Lý Hóa Đơn Điện Tử v2
Entry point — Điểm khởi động duy nhất.

Flow: Login popup → (thành công) → MainWindow.
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
    """Khởi động ứng dụng.

    Flow:
    1. Tạo hidden root + Login popup (Toplevel).
    2. Sau khi đăng nhập thành công → đóng root, tạo MainWindow.
    """
    setup_logging()
    logger = get_logger(__name__)
    logger.info(f"{'='*60}")
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"{'='*60}")

    print("[HDDT] Loading login UI...")
    import customtkinter as ctk
    ctk.set_appearance_mode("light")

    from app.ui.views.login_view import show_login_and_wait

    print("[HDDT] Showing login window...")
    login_result = show_login_and_wait()

    if not login_result:
        print("[HDDT] Login cancelled or failed. Exiting.")
        sys.exit(0)

    logged_mst = login_result.get("mst", "")
    logged_token = login_result.get("token", "")

    print("[HDDT] Login successful. Loading main window...")
    from app.ui.main_window import MainWindow

    app = MainWindow(skip_login=True, initial_mst=logged_mst, initial_token=logged_token)
    print("[HDDT] Window ready - showing now")
    app.deiconify()
    app.run()


if __name__ == "__main__":
    main()
