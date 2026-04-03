"""
MainWindow — Cửa sổ chính của ứng dụng.

Kiến trúc:
- Sidebar navigation (trái) — bao gồm nút Đăng nhập mở popup
- Content area (phải) — chứa các views (không còn login_view)
- Status bar (dưới)

Quản lý tất cả shared services (DB, API, Parsers...).
"""
import customtkinter as ctk
import threading
from typing import Dict, Optional

from config.settings import APP_NAME, APP_VERSION
from config.theme import get_colors, set_mode, get_mode, FONTS, SPACING
from config.logger import get_logger

from app.models.db_handler import DBHandler
from app.models.api_client import APIClient
from app.models.credential_store import CredentialStore

from app.services.auth_service import AuthService
from app.services.account_service import AccountService
from app.services.invoice_query_service import InvoiceQueryService
from app.services.invoice_parser_service import InvoiceParserService
from app.services.excel_export_service import ExcelExportService
from app.services.remote_config_service import RemoteConfigService

from app.ui.components.status_bar import StatusBar
from app.ui.components.toast import show_toast

logger = get_logger(__name__)


class MainWindow(ctk.CTk):
    """Cửa sổ chính — orchestrator cho toàn bộ UI."""

    def __init__(self):
        super().__init__()
        self.colors = get_colors()

        # ── Window config ────────────────────────────
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x760")
        self.minsize(1024, 600)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=self.colors["bg_primary"])

        # ── Init Services ────────────────────────────
        self.db = DBHandler()
        self.api_client = APIClient()
        self.credential_store = CredentialStore()

        self.auth_service = AuthService(self.api_client, self.credential_store)
        self.account_service = AccountService(self.db, self.credential_store)
        self.query_service = InvoiceQueryService(self.api_client, self.db)
        self.parser_service = InvoiceParserService(self.db)
        self.excel_service = ExcelExportService()
        self.remote_service = RemoteConfigService(self.db)

        logger.info("All services initialized")

        # ── Build UI ─────────────────────────────────
        self._views: Dict[str, ctk.CTkFrame] = {}
        self._current_view: Optional[str] = None
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._login_popup = None  # Track login popup

        self._build_ui()

        # ── Hiện cửa sổ trên cùng ───────────────────
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 1280) // 2
        y = (sh - 760) // 2
        self.geometry(f"1280x760+{x}+{y}")
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))

        # ── Background: Remote Config Check ──────────
        self._check_remote_config()

        # ── Cleanup on close ─────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═══════════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════════

    def _build_ui(self):
        c = self.colors

        # ── Status Bar (pack FIRST with side=bottom) ─
        self.status_bar = StatusBar(self)
        self.status_bar.pack(side="bottom", fill="x")

        # ── Sidebar ──────────────────────────────────
        self._sidebar = ctk.CTkFrame(
            self, width=200, fg_color=c["bg_secondary"], corner_radius=0,
        )
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Logo / Title
        logo_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent", height=70)
        logo_frame.pack(fill="x", padx=12, pady=(16, 8))
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(
            logo_frame, text="HDDT",
            font=("Inter", 24, "bold"),
            text_color=c["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text=f"v{APP_VERSION}",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
        ).pack(anchor="w")

        # Separator
        ctk.CTkFrame(self._sidebar, height=1, fg_color=c["border"]).pack(fill="x", padx=12, pady=8)

        # ── Login button (opens popup) ───────────────
        self._login_btn = ctk.CTkButton(
            self._sidebar,
            text="🔑 Đăng nhập",
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["accent"],
            hover_color=c["accent_hover"],
            text_color="#ffffff",
            anchor="w",
            height=40,
            corner_radius=8,
            command=self._open_login_popup,
        )
        self._login_btn.pack(fill="x", padx=8, pady=(0, 4))

        # Separator
        ctk.CTkFrame(self._sidebar, height=1, fg_color=c["border"]).pack(fill="x", padx=12, pady=4)

        # Nav buttons (without login)
        nav_items = [
            ("invoice_list", "📋 Danh sách HĐ", "invoice_list_view"),
            ("settings",     "⚙ Cài đặt",       "settings_view"),
        ]

        for key, text, view_name in nav_items:
            btn = ctk.CTkButton(
                self._sidebar,
                text=text,
                font=FONTS.get("body", ("Segoe UI", 13)),
                fg_color="transparent",
                hover_color=c["bg_tertiary"],
                text_color=c["text_secondary"],
                anchor="w",
                height=40,
                corner_radius=8,
                command=lambda v=view_name: self.show_view(v),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_buttons[view_name] = btn

        # ── Login status indicator ───────────────────
        self._login_status_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        self._login_status_frame.pack(fill="x", padx=12, pady=(8, 0))

        self._login_status_label = ctk.CTkLabel(
            self._login_status_frame,
            text="Chưa đăng nhập",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
            wraplength=170,
        )
        self._login_status_label.pack(anchor="w")

        # ── Bottom area: theme toggle + logout ───────
        bottom_container = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        bottom_container.pack(fill="both", expand=True)

        bottom_frame = ctk.CTkFrame(bottom_container, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=12, pady=12)

        # Logout button (hidden initially)
        self._logout_btn = ctk.CTkButton(
            bottom_frame,
            text="🚪 Đăng xuất",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            fg_color="transparent",
            hover_color=c["bg_tertiary"],
            text_color=c["error"],
            height=30, anchor="w",
            command=self.on_logout,
        )
        # Don't pack yet — show after login

        # Theme toggle
        self._theme_switch = ctk.CTkSwitch(
            bottom_frame,
            text="Dark Mode",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
            command=self._toggle_theme,
            progress_color=c["accent"],
        )
        self._theme_switch.pack(anchor="w", pady=(4, 0))

        # ── Content Area ─────────────────────────────
        self._content = ctk.CTkFrame(self, fg_color=c["bg_primary"], corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        # ── Init Views (lazy, no login view) ──────────
        self._init_views()

        # Show invoice list by default
        self.show_view("invoice_list_view")

    def _init_views(self):
        """Khởi tạo views (lazy loading) — login giờ là popup."""
        from app.ui.views.invoice_list_view import InvoiceListView
        from app.ui.views.settings_view import SettingsView

        self._views["invoice_list_view"] = InvoiceListView(self._content, self)
        self._views["settings_view"] = SettingsView(self._content, self)

    # ═══════════════════════════════════════════════════════
    # LOGIN POPUP
    # ═══════════════════════════════════════════════════════

    def _open_login_popup(self):
        """Mở popup đăng nhập."""
        if self._login_popup is not None:
            try:
                self._login_popup.focus_set()
                return
            except Exception:
                self._login_popup = None

        from app.ui.views.login_view import LoginPopup
        self._login_popup = LoginPopup(self, self)

        # Track when popup is closed
        def _on_popup_close():
            self._login_popup = None

        self._login_popup.bind("<Destroy>", lambda e: _on_popup_close())

    # ═══════════════════════════════════════════════════════
    # NAVIGATION
    # ═══════════════════════════════════════════════════════

    def show_view(self, view_name: str):
        """Chuyển đổi view."""
        c = self.colors

        # Hide current
        if self._current_view and self._current_view in self._views:
            self._views[self._current_view].pack_forget()

        # Show new
        if view_name in self._views:
            self._views[view_name].pack(fill="both", expand=True)
            self._current_view = view_name

        # Update nav highlight
        for name, btn in self._nav_buttons.items():
            if name == view_name:
                btn.configure(
                    fg_color=c["accent"],
                    text_color="#ffffff",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=c["text_secondary"],
                )

    # ═══════════════════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════════════════

    def _toggle_theme(self):
        mode = "dark" if self._theme_switch.get() else "light"
        set_mode(mode)
        ctk.set_appearance_mode(mode)
        self.colors = get_colors()

        # Refresh shell widgets
        self.configure(fg_color=self.colors["bg_primary"])
        self._sidebar.configure(fg_color=self.colors["bg_secondary"])
        self._content.configure(fg_color=self.colors["bg_primary"])

        # Text update on theme switch
        self._theme_switch.configure(
            text="Dark Mode" if mode == "dark" else "Light Mode",
            text_color=self.colors["text_muted"],
        )

        # Propagate theme to all views' DataTable instances
        for view_name, view in self._views.items():
            # Summary table
            if hasattr(view, '_summary_table') and hasattr(view._summary_table, 'refresh_theme'):
                view._summary_table.refresh_theme()
            # Detail table
            if hasattr(view, '_detail_table') and hasattr(view._detail_table, 'refresh_theme'):
                view._detail_table.refresh_theme()
            # Legacy single _table
            if hasattr(view, '_table') and hasattr(view._table, 'refresh_theme'):
                view._table.refresh_theme()

    # ═══════════════════════════════════════════════════════
    # REMOTE CONFIG
    # ═══════════════════════════════════════════════════════

    def _check_remote_config(self):
        """Background check remote config."""
        def _check():
            result = self.remote_service.auto_update()
            if result:
                self.after(0, lambda: show_toast(
                    self, f"API đã cập nhật: {result}", "success", 5000
                ))

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════

    def on_login_success(self, mst: str):
        """Callback khi đăng nhập thành công."""
        c = self.colors
        self.status_bar.set_status(f"MST: {mst}", connected=True)
        show_toast(self, f"Đăng nhập thành công: {mst}", "success")

        # Update sidebar login status
        self._login_status_label.configure(
            text=f"✅ {mst}",
            text_color=c["success"],
        )
        self._login_btn.configure(
            text=f"🔑 {mst[:10]}...",
            fg_color=c["success"],
            hover_color="#15803d",
        )

        # Show logout button
        self._logout_btn.pack(anchor="w", pady=(0, 4))

        # Show invoice view
        self.show_view("invoice_list_view")

    def on_logout(self):
        """Callback khi đăng xuất."""
        c = self.colors
        self.auth_service.logout()
        self.status_bar.set_status("Chưa đăng nhập", connected=False)
        show_toast(self, "Đã đăng xuất", "info")

        # Reset sidebar
        self._login_status_label.configure(
            text="Chưa đăng nhập",
            text_color=c["text_muted"],
        )
        self._login_btn.configure(
            text="🔑 Đăng nhập",
            fg_color=c["accent"],
            hover_color=c["accent_hover"],
        )
        self._logout_btn.pack_forget()

    def _on_close(self):
        """Cleanup khi đóng app."""
        try:
            self.api_client.close()
        except Exception:
            pass
        logger.info("Application closed")
        self.destroy()

    def run(self):
        """Chạy main loop."""
        logger.info("UI Main loop started")
        self.mainloop()
