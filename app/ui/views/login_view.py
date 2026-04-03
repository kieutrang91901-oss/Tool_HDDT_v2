"""
LoginView — Màn hình đăng nhập + quản lý tài khoản.

- Dropdown chọn MST đã lưu
- Captcha display + auto-fill (OCR)
- Quản lý tài khoản (thêm/sửa/xóa)
"""
import customtkinter as ctk
import threading
from io import BytesIO
from PIL import Image
from typing import Optional

from config.theme import get_colors, FONTS, SPACING
from config.logger import get_logger
from app.ui.components.toast import show_toast

logger = get_logger(__name__)


def _ocr_captcha(image_bytes: bytes) -> str:
    """Nhận diện captcha đơn giản bằng Pillow + pytesseract hoặc fallback.
    
    Cổng thuế dùng captcha số đơn giản (4-6 chữ số/ký tự).
    Thử dùng pytesseract nếu có, nếu không thì trả rỗng.
    """
    try:
        import pytesseract
        img = Image.open(BytesIO(image_bytes))

        # Preprocessing: convert to grayscale, threshold
        img = img.convert("L")  # Grayscale
        img = img.point(lambda p: 255 if p > 128 else 0)  # Binary threshold

        text = pytesseract.image_to_string(
            img, config="--psm 7 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ).strip()

        # Clean up: remove spaces and special chars
        text = "".join(c for c in text if c.isalnum())
        logger.info(f"OCR captcha result: {text}")
        return text
    except ImportError:
        logger.debug("pytesseract not installed — manual captcha entry required")
        return ""
    except Exception as e:
        logger.warning(f"OCR captcha failed: {e}")
        return ""


class LoginView(ctk.CTkFrame):
    """Màn hình đăng nhập cổng thuế."""

    def __init__(self, parent, main_window, **kwargs):
        colors = get_colors()
        super().__init__(parent, fg_color=colors["bg_primary"], **kwargs)
        self.main = main_window
        self.colors = colors
        self._captcha_key = ""

        self._build_ui()
        self._load_accounts()

        # Auto-load captcha khi mở view
        self.after(500, self._load_captcha)

    def _build_ui(self):
        c = self.colors

        # Center container
        center = ctk.CTkFrame(self, fg_color="transparent", width=420)
        center.place(relx=0.5, rely=0.45, anchor="center")

        # Title
        ctk.CTkLabel(
            center, text="Dang nhap Cong Thue",
            font=("Inter", 22, "bold"), text_color=c["accent"],
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            center, text="hoadondientu.gdt.gov.vn",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
        ).pack(pady=(0, 24))

        # Card
        card = ctk.CTkFrame(center, fg_color=c["bg_secondary"], corner_radius=12, width=400)
        card.pack(fill="x")

        # MST dropdown
        ctk.CTkLabel(card, text="Ma so thue", font=FONTS["body"], text_color=c["text_secondary"]).pack(anchor="w", padx=24, pady=(20, 4))
        self._mst_combo = ctk.CTkComboBox(
            card, values=[], width=352, height=36,
            font=FONTS.get("mono", ("Consolas", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            button_color=c["accent"], button_hover_color=c["accent_hover"],
            text_color=c["text_primary"],
            dropdown_fg_color=c["bg_secondary"],
            dropdown_text_color=c["text_primary"],
            dropdown_hover_color=c["bg_tertiary"],
            command=self._on_mst_select,
        )
        self._mst_combo.pack(padx=24)

        # Password
        ctk.CTkLabel(card, text="Mat khau", font=FONTS["body"], text_color=c["text_secondary"]).pack(anchor="w", padx=24, pady=(12, 4))
        self._pw_entry = ctk.CTkEntry(
            card, show="*", width=352, height=36,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            text_color=c["text_primary"],
        )
        self._pw_entry.pack(padx=24)

        # Captcha area
        captcha_frame = ctk.CTkFrame(card, fg_color="transparent")
        captcha_frame.pack(fill="x", padx=24, pady=(16, 0))

        # Captcha image
        self._captcha_label = ctk.CTkLabel(
            captcha_frame, text="Dang tai captcha...",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
            width=160, height=50,
            fg_color=c["bg_tertiary"], corner_radius=6,
        )
        self._captcha_label.pack(side="left")
        self._captcha_label.bind("<Button-1>", lambda e: self._load_captcha())

        # Captcha input
        self._captcha_entry = ctk.CTkEntry(
            captcha_frame, placeholder_text="Captcha...",
            width=120, height=36,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            text_color=c["text_primary"],
        )
        self._captcha_entry.pack(side="left", padx=(8, 0))

        # Refresh captcha button
        ctk.CTkButton(
            captcha_frame, text="Lam moi", width=60, height=36,
            font=("Segoe UI", 11),
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_primary"], corner_radius=6,
            command=self._load_captcha,
        ).pack(side="left", padx=(4, 0))

        # Login button
        self._login_btn = ctk.CTkButton(
            card, text="Dang nhap", width=352, height=42,
            font=FONTS.get("button", ("Segoe UI", 14, "bold")),
            fg_color=c["accent"], hover_color=c["accent_hover"],
            corner_radius=8,
            command=self._do_login,
        )
        self._login_btn.pack(padx=24, pady=(20, 8))
        self._captcha_entry.bind("<Return>", lambda e: self._do_login())

        # Status
        self._status = ctk.CTkLabel(
            card, text="",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
        )
        self._status.pack(pady=(0, 16))

        # Account management link
        mgmt_frame = ctk.CTkFrame(center, fg_color="transparent")
        mgmt_frame.pack(fill="x", pady=(16, 0))

        ctk.CTkButton(
            mgmt_frame, text="+ Them tai khoan", width=130, height=30,
            font=FONTS.get("caption", ("Segoe UI", 11)),
            fg_color="transparent", hover_color=c["bg_tertiary"],
            text_color=c["accent"],
            command=self._add_account_dialog,
        ).pack(side="left")

        ctk.CTkButton(
            mgmt_frame, text="Xoa tai khoan", width=110, height=30,
            font=FONTS.get("caption", ("Segoe UI", 11)),
            fg_color="transparent", hover_color=c["bg_tertiary"],
            text_color=c["error"],
            command=self._delete_account,
        ).pack(side="right")

    # ═══════════════════════════════════════════════════════
    # ACCOUNTS
    # ═══════════════════════════════════════════════════════

    def _load_accounts(self):
        accounts = self.main.account_service.get_all_accounts()
        values = [f"{a.mst} - {a.ten_cty}" if a.ten_cty else a.mst for a in accounts]
        self._mst_combo.configure(values=values)
        if values:
            self._mst_combo.set(values[0])
            self._on_mst_select(values[0])

    def _on_mst_select(self, choice: str):
        mst = choice.split(" - ")[0].strip()
        pw = self.main.account_service.get_password(mst)
        if pw:
            self._pw_entry.delete(0, "end")
            self._pw_entry.insert(0, pw)

    def _get_current_mst(self) -> str:
        return self._mst_combo.get().split(" - ")[0].strip()

    def _add_account_dialog(self):
        from app.ui.components.dialog import InputDialog

        def _on_submit(value):
            parts = value.split(",")
            mst = parts[0].strip()
            ten = parts[1].strip() if len(parts) > 1 else ""
            pw = parts[2].strip() if len(parts) > 2 else ""
            if mst:
                self.main.account_service.add_account(mst, pw, ten)
                self._load_accounts()
                show_toast(self.main, f"Da them: {mst}", "success")

        InputDialog(
            self, title="Them tai khoan",
            label="Nhap: MST, Ten CTY, Password (cach boi dau phay)",
            on_submit=_on_submit,
        )

    def _delete_account(self):
        mst = self._get_current_mst()
        if not mst:
            return
        from app.ui.components.dialog import ConfirmDialog
        ConfirmDialog(
            self, title="Xoa tai khoan",
            message=f"Ban co chac muon xoa tai khoan MST: {mst}?",
            on_confirm=lambda: self._do_delete(mst),
        )

    def _do_delete(self, mst):
        self.main.account_service.delete_account(mst)
        self._load_accounts()
        show_toast(self.main, f"Da xoa: {mst}", "info")

    # ═══════════════════════════════════════════════════════
    # CAPTCHA
    # ═══════════════════════════════════════════════════════

    def _load_captcha(self):
        self._status.configure(text="Dang lay captcha...", text_color=self.colors["text_muted"])
        self._captcha_entry.delete(0, "end")

        def _fetch():
            result = self.main.auth_service.get_captcha()
            self.after(0, lambda: self._show_captcha(result))

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_captcha(self, result):
        if result.success and result.image_bytes:
            try:
                self._captcha_key = result.captcha_key

                if getattr(result, 'content_type', '') == 'svg':
                    # Try native SVG display first (no conversion needed)
                    if self._show_captcha_svg_native(result.image_bytes):
                        self._status.configure(text="Nhap captcha roi dang nhap")
                        self._captcha_entry.focus()
                        return

                    # Fallback: convert SVG to PIL Image
                    img = self._svg_to_image(result.image_bytes)
                else:
                    # Binary image (PNG/JPEG)
                    img = Image.open(BytesIO(result.image_bytes))

                if img:
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 50))
                    self._captcha_label.configure(image=ctk_img, text="")
                else:
                    self._captcha_label.configure(text="[Captcha - nhap thu cong]", image=None)

                # Auto-fill captcha via OCR (only for raster images)
                if img and getattr(result, 'content_type', '') != 'svg':
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    ocr_text = _ocr_captcha(buf.getvalue())
                    if ocr_text:
                        self._captcha_entry.delete(0, "end")
                        self._captcha_entry.insert(0, ocr_text)
                        self._status.configure(
                            text=f"Captcha tu dong: {ocr_text}",
                            text_color=self.colors["success"],
                        )
                        return

                self._status.configure(text="Nhap captcha roi dang nhap")
                self._captcha_entry.focus()
            except Exception as e:
                self._status.configure(text=f"Loi hien thi captcha: {e}")
                logger.error(f"Captcha display error: {e}")
        else:
            err_msg = result.error_msg or "Khong ket noi duoc cong thue"
            self._status.configure(text=f"Loi: {err_msg}", text_color=self.colors["warning"])
            self._captcha_label.configure(text="Nhan de thu lai", image=None)

    def _svg_to_image(self, svg_bytes: bytes) -> Optional[Image.Image]:
        """Chuyển SVG bytes sang PIL Image."""
        # Method 1: tksvg — native tkinter SVG support
        try:
            import tksvg
            import tkinter as tk

            svg_data = svg_bytes.decode("utf-8")
            # Tạo PhotoImage từ SVG data
            photo = tksvg.SvgImage(data=svg_data, scaletowidth=200)

            # Convert tkinter PhotoImage -> PIL Image
            width = photo.width()
            height = photo.height()
            # Use a temporary hidden canvas to render
            canvas = tk.Canvas(self, width=width, height=height)
            canvas.create_image(0, 0, anchor="nw", image=photo)
            canvas.update_idletasks()

            # Get pixels via postscript (fallback: use PhotoImage directly)
            # Store reference to prevent garbage collection
            self._captcha_photo = photo

            # Instead of converting, use CTkImage from tkinter PhotoImage directly
            img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
            # tksvg doesn't easily provide pixel data, so we use a workaround:
            # Create PIL image from the raw data string
            try:
                data = photo.data  # type: ignore
                if data:
                    import base64 as b64mod
                    png_data = b64mod.b64decode(data)
                    img = Image.open(BytesIO(png_data))
            except Exception:
                pass

            canvas.destroy()
            return img
        except ImportError:
            logger.debug("tksvg not installed")
        except Exception as e:
            logger.debug(f"tksvg render failed: {e}")

        # Method 2: cairosvg
        try:
            import cairosvg
            png_data = cairosvg.svg2png(bytestring=svg_bytes, output_width=200, output_height=50)
            return Image.open(BytesIO(png_data))
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"cairosvg failed: {e}")

        logger.info("No SVG renderer available")
        return None

    def _show_captcha_svg_native(self, svg_bytes: bytes):
        """Hiển thị SVG captcha trực tiếp qua tksvg (no PIL conversion)."""
        try:
            import tksvg
            svg_data = svg_bytes.decode("utf-8")
            photo = tksvg.SvgImage(data=svg_data, scaletowidth=160, scaletoheight=50)
            self._captcha_photo = photo  # Prevent GC
            self._captcha_label.configure(image=photo, text="")
            return True
        except Exception as e:
            logger.debug(f"SVG native display failed: {e}")
            return False

    # ═══════════════════════════════════════════════════════
    # LOGIN
    # ═══════════════════════════════════════════════════════

    def _do_login(self):
        mst = self._get_current_mst()
        password = self._pw_entry.get()
        captcha = self._captcha_entry.get().strip()

        if not mst:
            self._status.configure(text="Vui long chon MST", text_color=self.colors["error"])
            return
        if not password:
            self._status.configure(text="Vui long nhap mat khau", text_color=self.colors["error"])
            return
        if not captcha:
            self._status.configure(text="Vui long nhap captcha", text_color=self.colors["error"])
            return

        self._login_btn.configure(state="disabled", text="Dang dang nhap...")
        self._status.configure(text="Dang ket noi...", text_color=self.colors["text_muted"])

        def _login_thread():
            result = self.main.auth_service.login(mst, password, captcha, self._captcha_key)
            self.after(0, lambda: self._on_login_result(result, mst, password))

        threading.Thread(target=_login_thread, daemon=True).start()

    def _on_login_result(self, result, mst, password):
        self._login_btn.configure(state="normal", text="Dang nhap")

        if result.success:
            # Lưu password nếu chưa có
            if not self.main.account_service.has_password(mst):
                self.main.account_service.add_account(mst, password)
            self._status.configure(text="Dang nhap thanh cong!", text_color=self.colors["success"])
            self.main.on_login_success(mst)
        else:
            self._status.configure(text=f"Loi: {result.error_msg}", text_color=self.colors["error"])
            self._load_captcha()  # Refresh captcha
