"""
SettingsView — Cài đặt ứng dụng.

Quản lý: Tài khoản, Theme, Remote Config, About.
"""
import customtkinter as ctk
from config.theme import get_colors, FONTS, get_mode
from config.settings import APP_NAME, APP_VERSION, DATA_DIR
from config.logger import get_logger
from app.ui.components.toast import show_toast

logger = get_logger(__name__)


class SettingsView(ctk.CTkFrame):
    """Màn hình cài đặt."""

    def __init__(self, parent, main_window, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color=colors["bg_primary"], **kwargs)
        self.main = main_window
        self.colors = colors

        self._build_ui()

    def _build_ui(self):
        c = self.colors

        scroll = ctk.CTkScrollableFrame(self, fg_color=c["bg_primary"])
        scroll.pack(fill="both", expand=True, padx=24, pady=16)

        # ── Header ───────────────────────────────────
        ctk.CTkLabel(
            scroll, text="Cài đặt",
            font=("Inter", 22, "bold"), text_color=c["accent"],
        ).pack(anchor="w", pady=(0, 20))

        # ══════════════════════════════════════════════
        # SECTION: TỔNG QUAN
        # ══════════════════════════════════════════════
        self._section_header(scroll, "Tổng quan")

        info_card = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
        info_card.pack(fill="x", pady=(0, 16))

        infos = [
            ("Ứng dụng", f"{APP_NAME} v{APP_VERSION}"),
            ("Dữ liệu", DATA_DIR),
            ("Keyring", "Có" if self.main.credential_store.is_available() else "Không"),
            ("Theme", get_mode().capitalize()),
        ]
        for label, val in infos:
            self._info_row(info_card, label, val)

        # ══════════════════════════════════════════════
        # SECTION: TÀI KHOẢN
        # ══════════════════════════════════════════════
        self._section_header(scroll, "Tài khoản đã lưu")

        accounts = self.main.account_service.get_all_accounts()
        if accounts:
            acc_card = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
            acc_card.pack(fill="x", pady=(0, 16))

            for acc in accounts:
                row = ctk.CTkFrame(acc_card, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=6)

                status = "●" if acc.is_active else "○"
                color = c["success"] if acc.is_active else c["text_muted"]

                ctk.CTkLabel(
                    row, text=f"{status} {acc.mst}",
                    font=FONTS.get("mono", ("Consolas", 13)),
                    text_color=color,
                ).pack(side="left")

                ctk.CTkLabel(
                    row, text=acc.ten_cty or "(chưa đặt tên)",
                    font=FONTS.get("body", ("Segoe UI", 13)),
                    text_color=c["text_secondary"],
                ).pack(side="left", padx=(16, 0))

                pw_status = "🔑" if self.main.account_service.has_password(acc.mst) else "○"
                ctk.CTkLabel(
                    row, text=pw_status,
                    font=("Segoe UI", 14),
                    text_color=c["text_muted"],
                ).pack(side="right")
        else:
            ctk.CTkLabel(
                scroll, text="Chưa có tài khoản nào. Hãy thêm ở màn hình Đăng nhập.",
                font=FONTS.get("body", ("Segoe UI", 13)),
                text_color=c["text_muted"],
            ).pack(anchor="w", pady=(0, 16))

        # ══════════════════════════════════════════════
        # SECTION: REMOTE CONFIG
        # ══════════════════════════════════════════════
        self._section_header(scroll, "Remote Config")

        rc_card = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
        rc_card.pack(fill="x", pady=(0, 16))

        from config.api_config import GDT_API_Config as API
        rc_infos = [
            ("API Version", API.VERSION),
            ("Remote URL", self.main.remote_service.get_remote_url()),
        ]

        cached = self.main.db.get_remote_config()
        if cached:
            rc_infos.append(("Last checked", cached.get("last_checked", "—")))
            rc_infos.append(("Cached version", cached.get("version", "—")))

        for label, val in rc_infos:
            self._info_row(rc_card, label, str(val))

        ctk.CTkButton(
            rc_card, text="Kiểm tra cập nhật", width=150, height=32,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["accent"], hover_color=c["accent_hover"],
            command=self._check_remote,
        ).pack(padx=16, pady=12, anchor="w")

        # ══════════════════════════════════════════════
        # SECTION: FIELD REGISTRY
        # ══════════════════════════════════════════════
        self._section_header(scroll, "Fields đã phát hiện (Auto-Discovery)")

        fields = self.main.parser_service.get_discovered_fields()
        if fields:
            fr_card = ctk.CTkFrame(scroll, fg_color=c["bg_secondary"], corner_radius=8)
            fr_card.pack(fill="x", pady=(0, 16))

            for f in fields:
                row = ctk.CTkFrame(fr_card, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=3)

                ctk.CTkLabel(
                    row, text=f["scope"],
                    font=FONTS.get("mono_sm", ("Consolas", 11)),
                    text_color=c["accent_light"], width=70,
                ).pack(side="left")

                ctk.CTkLabel(
                    row, text=f["field_key"],
                    font=FONTS.get("body", ("Segoe UI", 13)),
                    text_color=c["text_primary"],
                ).pack(side="left", padx=(8, 0))

                ctk.CTkLabel(
                    row, text=f"x{f['seen_count']}",
                    font=FONTS.get("caption", ("Segoe UI", 11)),
                    text_color=c["text_muted"],
                ).pack(side="right")
        else:
            ctk.CTkLabel(
                scroll, text="Chưa có field nào. Hãy import file XML để hệ thống tự phát hiện.",
                font=FONTS.get("body", ("Segoe UI", 13)),
                text_color=c["text_muted"],
            ).pack(anchor="w", pady=(0, 16))

        # ══════════════════════════════════════════════
        # SECTION: ĐĂNG XUẤT
        # ══════════════════════════════════════════════

        ctk.CTkFrame(scroll, height=1, fg_color=c["border"]).pack(fill="x", pady=20)

        if self.main.auth_service.is_logged_in:
            ctk.CTkButton(
                scroll, text="Đăng xuất", width=120, height=36,
                font=FONTS.get("body", ("Segoe UI", 13)),
                fg_color=c["error"], hover_color="#dc2626",
                command=self.main.on_logout,
            ).pack(anchor="w")

    # ═══════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════

    def _section_header(self, parent, title: str):
        ctk.CTkLabel(
            parent, text=title,
            font=FONTS.get("heading_sm", ("Segoe UI", 14, "bold")),
            text_color=self.colors["text_primary"],
        ).pack(anchor="w", pady=(16, 8))

    def _info_row(self, parent, label: str, value: str):
        c = self.colors
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            row, text=label, width=140, anchor="w",
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=c["text_muted"],
        ).pack(side="left")

        ctk.CTkLabel(
            row, text=value, anchor="w",
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=c["text_primary"],
            wraplength=400,
        ).pack(side="left", fill="x", expand=True)

    def _check_remote(self):
        import threading

        def _check():
            result = self.main.remote_service.check_for_updates()
            if result.has_update:
                self.main.remote_service.apply_update(result.remote_data)
                self.after(0, lambda: show_toast(
                    self.main, f"Đã cập nhật API v{result.remote_version}", "success"
                ))
            else:
                self.after(0, lambda: show_toast(
                    self.main,
                    result.error_msg or "Đang dùng phiên bản mới nhất",
                    "info"
                ))

        threading.Thread(target=_check, daemon=True).start()
