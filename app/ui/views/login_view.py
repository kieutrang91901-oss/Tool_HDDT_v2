"""
LoginView — Popup đăng nhập nhỏ gọn.

- CTkToplevel thay vì fullscreen frame
- Tự đóng sau khi đăng nhập thành công
- Captcha display + auto-fill (SVG Solver)
"""
import customtkinter as ctk
import threading
import re
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageDraw
from typing import Optional, List, Tuple

from config.theme import get_colors, FONTS, SPACING
from config.logger import get_logger
from app.ui.components.toast import show_toast
from app.services.captcha_solver import get_captcha_solver

logger = get_logger(__name__)


def _solve_svg_captcha(svg_content: str) -> str:
    """Giải captcha SVG bằng CaptchaSolver (pattern matching trên path commands)."""
    try:
        solver = get_captcha_solver()
        result = solver.solve(svg_content)
        if result:
            logger.info(f"SVG captcha solved: {result}")
        else:
            logger.warning("SVG captcha: no characters recognized")
        return result
    except Exception as e:
        logger.error(f"SVG captcha solver error: {e}")
        return ""


def _svg_to_pil_image(svg_bytes: bytes, width: int = 160, height: int = 50) -> Optional[Image.Image]:
    """Render SVG thành PIL Image bằng cách parse paths và vẽ lên canvas."""
    try:
        svg_text = svg_bytes.decode("utf-8", errors="replace")

        vb_match = re.search(r'viewBox="([^"]+)"', svg_text)
        if vb_match:
            parts = vb_match.group(1).split()
            if len(parts) == 4:
                svg_w = float(parts[2])
                svg_h = float(parts[3])
            else:
                svg_w, svg_h = 200, 70
        else:
            w_match = re.search(r'width="(\d+)"', svg_text)
            h_match = re.search(r'height="(\d+)"', svg_text)
            svg_w = float(w_match.group(1)) if w_match else 200
            svg_h = float(h_match.group(1)) if h_match else 70

        scale_x = width / svg_w
        scale_y = height / svg_h
        scale = min(scale_x, scale_y)

        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        paths = re.findall(r'd="([^"]+)"', svg_text)
        fills = re.findall(r'fill="([^"]+)"', svg_text)

        for idx, path_data in enumerate(paths):
            fill_color = "#333333"
            if idx < len(fills):
                fc = fills[idx]
                if fc and fc != "none" and not fc.startswith("url"):
                    fill_color = fc

            points = _parse_svg_path_to_points(path_data, scale)

            if len(points) >= 2:
                draw.line(points, fill=fill_color, width=2)

        return img
    except Exception as e:
        logger.debug(f"SVG to PIL fallback rendering failed: {e}")
        return None


def _parse_svg_path_to_points(
    path_data: str, scale: float
) -> List[Tuple[float, float]]:
    """Parse SVG path data (M, Q, Z commands) thành list tọa độ."""
    points: List[Tuple[float, float]] = []
    tokens = re.findall(r'([MmQqLlCcZz])([^MmQqLlCcZz]*)', path_data)

    cx, cy = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    for cmd, args_str in tokens:
        nums = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', args_str)]

        if cmd == 'M':
            if len(nums) >= 2:
                cx, cy = nums[0] * scale, nums[1] * scale
                start_x, start_y = cx, cy
                points.append((cx, cy))
        elif cmd == 'Q':
            i = 0
            while i + 3 < len(nums):
                cx = nums[i + 2] * scale
                cy = nums[i + 3] * scale
                points.append((cx, cy))
                i += 4
        elif cmd == 'L':
            i = 0
            while i + 1 < len(nums):
                cx = nums[i] * scale
                cy = nums[i + 1] * scale
                points.append((cx, cy))
                i += 2
        elif cmd == 'Z' or cmd == 'z':
            points.append((start_x, start_y))
            cx, cy = start_x, start_y

    return points


class LoginPopup(ctk.CTkToplevel):
    """Popup đăng nhập cổng thuế — nhỏ gọn, tự đóng sau khi login."""

    def __init__(self, parent, main_window, **kwargs):
        super().__init__(parent, **kwargs)
        self.main = main_window
        self.colors = get_colors()
        self._captcha_key = ""
        self._is_destroyed = False

        # ── Window config ─────────────────────────
        self.title("Đăng nhập Cổng Thuế")
        self.geometry("440x520")
        self.resizable(False, False)
        self.configure(fg_color=self.colors["bg_primary"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # Prevent closing while logging in
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._load_accounts()

        # Center on parent
        self._center()

        # Auto-load captcha
        self.after(300, self._load_captcha)

    def _build_ui(self):
        c = self.colors

        # ── Title area ───────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color=c["accent"], height=64, corner_radius=0)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        ctk.CTkLabel(
            title_frame, text="🔑  Đăng nhập Cổng Thuế",
            font=("Inter", 17, "bold"), text_color="#ffffff",
        ).pack(side="left", padx=20)
        ctk.CTkLabel(
            title_frame, text="hoadondientu.gdt.gov.vn",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color="#c0c0c0",
        ).pack(side="right", padx=20)

        # ── Form (card) ──────────────────────────
        card = ctk.CTkFrame(self, fg_color=c["bg_secondary"], corner_radius=12)
        card.pack(fill="x", padx=16, pady=16)

        # MST dropdown
        ctk.CTkLabel(
            card, text="Mã số thuế",
            font=FONTS["body"], text_color=c["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(16, 4))

        self._mst_combo = ctk.CTkComboBox(
            card, values=[], height=36,
            font=FONTS.get("mono", ("Consolas", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            button_color=c["accent"], button_hover_color=c["accent_hover"],
            text_color=c["text_primary"],
            dropdown_fg_color=c["bg_secondary"],
            dropdown_text_color=c["text_primary"],
            dropdown_hover_color=c["bg_tertiary"],
            command=self._on_mst_select,
        )
        self._mst_combo.pack(fill="x", padx=20)

        # Password
        ctk.CTkLabel(
            card, text="Mật khẩu",
            font=FONTS["body"], text_color=c["text_secondary"],
        ).pack(anchor="w", padx=20, pady=(12, 4))

        self._pw_entry = ctk.CTkEntry(
            card, show="*", height=36,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            text_color=c["text_primary"],
        )
        self._pw_entry.pack(fill="x", padx=20)

        # Captcha area
        captcha_frame = ctk.CTkFrame(card, fg_color="transparent")
        captcha_frame.pack(fill="x", padx=20, pady=(14, 0))

        self._captcha_label = ctk.CTkLabel(
            captcha_frame, text="Đang tải captcha...",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
            width=160, height=50,
            fg_color=c["bg_tertiary"], corner_radius=6,
        )
        self._captcha_label.pack(side="left")
        self._captcha_label.bind("<Button-1>", lambda e: self._load_captcha())

        self._captcha_entry = ctk.CTkEntry(
            captcha_frame, placeholder_text="Captcha...",
            width=120, height=36,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            text_color=c["text_primary"],
        )
        self._captcha_entry.pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            captcha_frame, text="↻", width=36, height=36,
            font=("Segoe UI", 16),
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_primary"], corner_radius=6,
            command=self._load_captcha,
        ).pack(side="left", padx=(4, 0))

        # Login button
        self._login_btn = ctk.CTkButton(
            card, text="Đăng nhập", height=42,
            font=FONTS.get("button", ("Segoe UI", 14, "bold")),
            fg_color=c["accent"], hover_color=c["accent_hover"],
            corner_radius=8,
            command=self._do_login,
        )
        self._login_btn.pack(fill="x", padx=20, pady=(16, 8))
        self._captcha_entry.bind("<Return>", lambda e: self._do_login())

        # Status
        self._status = ctk.CTkLabel(
            card, text="",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
        )
        self._status.pack(pady=(0, 12))

        # ── Account management ─────────────────────
        mgmt_frame = ctk.CTkFrame(self, fg_color="transparent")
        mgmt_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            mgmt_frame, text="+ Thêm tài khoản", width=130, height=30,
            font=FONTS.get("caption", ("Segoe UI", 11)),
            fg_color="transparent", hover_color=c["bg_tertiary"],
            text_color=c["accent"],
            command=self._add_account_dialog,
        ).pack(side="left")

        ctk.CTkButton(
            mgmt_frame, text="Xóa tài khoản", width=110, height=30,
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
                show_toast(self.main, f"Đã thêm: {mst}", "success")

        InputDialog(
            self, title="Thêm tài khoản",
            label="Nhập: MST, Tên CTY, Password (cách bởi dấu phẩy)",
            on_submit=_on_submit,
        )

    def _delete_account(self):
        mst = self._get_current_mst()
        if not mst:
            return
        from app.ui.components.dialog import ConfirmDialog
        ConfirmDialog(
            self, title="Xóa tài khoản",
            message=f"Bạn có chắc muốn xóa tài khoản MST: {mst}?",
            on_confirm=lambda: self._do_delete(mst),
        )

    def _do_delete(self, mst):
        self.main.account_service.delete_account(mst)
        self._load_accounts()
        show_toast(self.main, f"Đã xóa: {mst}", "info")

    # ═══════════════════════════════════════════════════════
    # CAPTCHA
    # ═══════════════════════════════════════════════════════

    def _load_captcha(self):
        if self._is_destroyed:
            return
        self._status.configure(text="Đang lấy captcha...", text_color=self.colors["text_muted"])
        self._captcha_entry.delete(0, "end")

        def _fetch():
            result = self.main.auth_service.get_captcha()
            if not self._is_destroyed:
                self.after(0, lambda: self._show_captcha(result))

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_captcha(self, result):
        if self._is_destroyed:
            return
        if result.success and result.image_bytes:
            try:
                self._captcha_key = result.captcha_key
                solved_text = ""
                img = None

                if getattr(result, 'content_type', '') == 'svg':
                    svg_content = result.image_bytes.decode("utf-8", errors="replace")
                    solved_text = _solve_svg_captcha(svg_content)

                    if self._show_captcha_svg_native(result.image_bytes):
                        pass
                    else:
                        img = self._svg_to_image(result.image_bytes)
                        if img:
                            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 50))
                            self._captcha_label.configure(image=ctk_img, text="")
                        else:
                            img = _svg_to_pil_image(result.image_bytes)
                            if img:
                                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 50))
                                self._captcha_label.configure(image=ctk_img, text="")
                            else:
                                if solved_text:
                                    self._captcha_label.configure(
                                        text=f"[SVG] Đã giải: {solved_text}",
                                        image=None,
                                    )
                                else:
                                    self._captcha_label.configure(
                                        text="[SVG Captcha - nhập thủ công]",
                                        image=None,
                                    )
                else:
                    img = Image.open(BytesIO(result.image_bytes))
                    if img:
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 50))
                        self._captcha_label.configure(image=ctk_img, text="")

                if solved_text:
                    self._captcha_entry.delete(0, "end")
                    self._captcha_entry.insert(0, solved_text)
                    self._status.configure(
                        text=f"✅ Captcha tự động: {solved_text}",
                        text_color=self.colors["success"],
                    )
                    logger.info(f"Captcha auto-filled: {solved_text}")
                    self._captcha_entry.focus()
                    return

                self._status.configure(text="Nhập captcha rồi đăng nhập")
                self._captcha_entry.focus()
            except Exception as e:
                self._status.configure(text=f"Lỗi hiển thị captcha: {e}")
                logger.error(f"Captcha display error: {e}")
        else:
            err_msg = result.error_msg or "Không kết nối được cổng thuế"
            self._status.configure(text=f"Lỗi: {err_msg}", text_color=self.colors["warning"])
            self._captcha_label.configure(text="Nhấn để thử lại", image=None)

    def _svg_to_image(self, svg_bytes: bytes) -> Optional[Image.Image]:
        """Chuyển SVG bytes sang PIL Image."""
        try:
            import tksvg
            import tkinter as tk

            svg_data = svg_bytes.decode("utf-8")
            photo = tksvg.SvgImage(data=svg_data, scaletowidth=200)
            width = photo.width()
            height = photo.height()
            canvas = tk.Canvas(self, width=width, height=height)
            canvas.create_image(0, 0, anchor="nw", image=photo)
            canvas.update_idletasks()
            self._captcha_photo = photo
            img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
            try:
                data = photo.data
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
        """Hiển thị SVG captcha trực tiếp qua tksvg."""
        try:
            import tksvg
            svg_data = svg_bytes.decode("utf-8")
            photo = tksvg.SvgImage(data=svg_data, scaletowidth=160, scaletoheight=50)
            self._captcha_photo = photo
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
            self._status.configure(text="Vui lòng chọn MST", text_color=self.colors["error"])
            return
        if not password:
            self._status.configure(text="Vui lòng nhập mật khẩu", text_color=self.colors["error"])
            return
        if not captcha:
            self._status.configure(text="Vui lòng nhập captcha", text_color=self.colors["error"])
            return

        self._login_btn.configure(state="disabled", text="Đang đăng nhập...")
        self._status.configure(text="Đang kết nối...", text_color=self.colors["text_muted"])

        def _login_thread():
            result = self.main.auth_service.login(mst, password, captcha, self._captcha_key)
            if not self._is_destroyed:
                self.after(0, lambda: self._on_login_result(result, mst, password))

        threading.Thread(target=_login_thread, daemon=True).start()

    def _on_login_result(self, result, mst, password):
        if self._is_destroyed:
            return
        self._login_btn.configure(state="normal", text="Đăng nhập")

        if result.success:
            if not self.main.account_service.has_password(mst):
                self.main.account_service.add_account(mst, password)
            self._status.configure(text="Đăng nhập thành công!", text_color=self.colors["success"])
            # Callback to main window, then close popup
            self.main.on_login_success(mst)
            self.after(500, self._close_popup)
        else:
            self._status.configure(text=f"Lỗi: {result.error_msg}", text_color=self.colors["error"])
            self._load_captcha()

    def _close_popup(self):
        """Đóng popup sau khi login thành công."""
        self._is_destroyed = True
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass

    def _on_close(self):
        """Xử lý khi user đóng popup."""
        self._is_destroyed = True
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass

    def _center(self):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w, h = 440, 520
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
