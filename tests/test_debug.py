"""Diagnostic: tìm chính xác bước nào gây treo/crash."""
import sys, os, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# Đảm bảo project root trong sys.path 
PROJECT_ROOT = r'd:\09. Python\05.DuAn\1.1.Tool_HDDT_v2'
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

print("Step 1: config imports...")
try:
    from config.settings import APP_NAME, APP_VERSION
    from config.logger import setup_logging, get_logger
    from config.theme import get_colors
    print(f"  OK: {APP_NAME} v{APP_VERSION}")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 2: customtkinter + tksheet...")
try:
    import customtkinter as ctk
    import tksheet
    print(f"  OK: CTK={ctk.__version__}, tksheet={tksheet.__version__}")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 3: models...")
try:
    from app.models.db_handler import DBHandler
    from app.models.api_client import APIClient
    from app.models.credential_store import CredentialStore
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 4: services...")
try:
    from app.services.auth_service import AuthService
    from app.services.account_service import AccountService
    from app.services.invoice_query_service import InvoiceQueryService
    from app.services.invoice_parser_service import InvoiceParserService
    from app.services.excel_export_service import ExcelExportService
    from app.services.remote_config_service import RemoteConfigService
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 5: UI imports...")
try:
    from app.ui.components.status_bar import StatusBar
    from app.ui.components.toast import show_toast
    print("  OK: Components")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 6: MainWindow import...")
try:
    from app.ui.main_window import MainWindow
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 7: Creating CTk root (no mainloop)...")
try:
    setup_logging()
    app = ctk.CTk()
    app.title("Test HDDT")
    app.geometry("300x200")
    ctk.CTkLabel(app, text="Test OK!", font=("Segoe UI", 16)).pack(pady=30)
    app.update()
    print(f"  OK: Window created, visible={app.winfo_viewable()}, w={app.winfo_width()}, h={app.winfo_height()}")
    app.destroy()
    print("  OK: Window destroyed")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

print("Step 8: Creating MainWindow (no mainloop)...")
try:
    app2 = MainWindow()
    app2.update()
    print(f"  OK: MainWindow created, visible={app2.winfo_viewable()}, w={app2.winfo_width()}, h={app2.winfo_height()}")
    app2.destroy()
    print("  OK: MainWindow destroyed")
except Exception as e:
    print(f"  FAIL at MainWindow: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n=== ALL STEPS PASSED ===")
