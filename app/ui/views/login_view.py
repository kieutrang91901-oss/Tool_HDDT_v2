"""
LoginView — Popup đăng nhập nhỏ gọn.

Có 2 class:
- StandaloneLoginWindow: CTk root window, dùng khi khởi động app (không cần parent).
- LoginPopup: CTkToplevel, dùng khi re-login từ MainWindow.

Features:
- Captcha display + auto-fill (SVG Solver)
- Show/Hide password toggle
- mandatory mode: bắt buộc đăng nhập khi khởi động
"""
import customtkinter as ctk
import threading
import re
import tkinter as tk
from io import BytesIO
from PIL import Image, ImageDraw, ImageTk
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


def _render_svg_to_pil(svg_bytes: bytes, width: int = 200, height: int = 70) -> Optional[Image.Image]:
    """Render SVG captcha thành PIL Image bằng cách vẽ trực tiếp lên PIL canvas.
    
    Parse SVG path data và vẽ với Pillow ImageDraw,
    hỗ trợ M, Q (Quadratic Bezier), L, C (Cubic Bezier), Z commands.
    """
    try:
        svg_text = svg_bytes.decode("utf-8", errors="replace")

        # Parse viewBox for proper scaling
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

        # Create white canvas
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Extract <path d="..." fill="..." /> elements
        path_pattern = re.compile(
            r'<path[^>]*?d="([^"]+)"[^>]*?>',
            re.DOTALL
        )
        path_elements = re.findall(r'<path[^>]*?/>', svg_text)
        if not path_elements:
            path_elements = re.findall(r'<path[^>]*?>[^<]*</path>', svg_text)

        for elem in path_elements:
            # Get path data
            d_match = re.search(r'd="([^"]+)"', elem)
            if not d_match:
                continue
            path_data = d_match.group(1)

            # Get fill color
            fill_match = re.search(r'fill="([^"]+)"', elem)
            fill_color = "#333333"
            if fill_match:
                fc = fill_match.group(1)
                if fc and fc != "none" and not fc.startswith("url"):
                    fill_color = fc

            # Parse path data into line segments via bezier interpolation
            segments = _parse_svg_path_segments(path_data, scale_x, scale_y)

            for seg_points in segments:
                if len(seg_points) >= 2:
                    # Draw as a filled polygon if closed, else as lines
                    flat = [coord for pt in seg_points for coord in pt]
                    if len(seg_points) >= 3:
                        try:
                            draw.polygon(flat, fill=fill_color)
                        except Exception:
                            draw.line(flat, fill=fill_color, width=2)
                    else:
                        draw.line(flat, fill=fill_color, width=2)

        return img
    except Exception as e:
        logger.debug(f"SVG to PIL rendering failed: {e}")
        return None


def _parse_svg_path_segments(
    path_data: str, scale_x: float, scale_y: float
) -> List[List[Tuple[float, float]]]:
    """Parse SVG path data thành các segments (subpaths).
    
    Hỗ trợ: M, Q (Quadratic Bezier), L, C (Cubic Bezier), Z.
    Interpolate bezier curves thành line segments.
    """
    segments: List[List[Tuple[float, float]]] = []
    current_segment: List[Tuple[float, float]] = []
    tokens = re.findall(r'([MmQqLlCcZz])([^MmQqLlCcZz]*)', path_data)

    cx, cy = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    for cmd, args_str in tokens:
        nums = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', args_str)]

        if cmd == 'M':
            if current_segment and len(current_segment) >= 2:
                segments.append(current_segment)
            current_segment = []
            if len(nums) >= 2:
                cx, cy = nums[0] * scale_x, nums[1] * scale_y
                start_x, start_y = cx, cy
                current_segment.append((cx, cy))
        elif cmd == 'Q':
            # Quadratic Bezier: control point + end point
            i = 0
            while i + 3 < len(nums):
                cpx = nums[i] * scale_x
                cpy = nums[i + 1] * scale_y
                ex = nums[i + 2] * scale_x
                ey = nums[i + 3] * scale_y
                # Interpolate quadratic bezier
                steps = 8
                for t_i in range(1, steps + 1):
                    t = t_i / steps
                    mt = 1 - t
                    px = mt * mt * cx + 2 * mt * t * cpx + t * t * ex
                    py = mt * mt * cy + 2 * mt * t * cpy + t * t * ey
                    current_segment.append((px, py))
                cx, cy = ex, ey
                i += 4
        elif cmd == 'C':
            # Cubic Bezier
            i = 0
            while i + 5 < len(nums):
                cp1x = nums[i] * scale_x
                cp1y = nums[i + 1] * scale_y
                cp2x = nums[i + 2] * scale_x
                cp2y = nums[i + 3] * scale_y
                ex = nums[i + 4] * scale_x
                ey = nums[i + 5] * scale_y
                steps = 8
                for t_i in range(1, steps + 1):
                    t = t_i / steps
                    mt = 1 - t
                    px = mt**3 * cx + 3 * mt**2 * t * cp1x + 3 * mt * t**2 * cp2x + t**3 * ex
                    py = mt**3 * cy + 3 * mt**2 * t * cp1y + 3 * mt * t**2 * cp2y + t**3 * ey
                    current_segment.append((px, py))
                cx, cy = ex, ey
                i += 6
        elif cmd == 'L':
            i = 0
            while i + 1 < len(nums):
                cx = nums[i] * scale_x
                cy = nums[i + 1] * scale_y
                current_segment.append((cx, cy))
                i += 2
        elif cmd in ('Z', 'z'):
            current_segment.append((start_x, start_y))
            cx, cy = start_x, start_y
            segments.append(current_segment)
            current_segment = []

    if current_segment and len(current_segment) >= 2:
        segments.append(current_segment)

    return segments


# ══════════════════════════════════════════════════════════════
# MIXIN: Logic đăng nhập dùng chung cho cả 2 class
# ══════════════════════════════════════════════════════════════

class _LoginMixin:
    """Mixin chứa logic UI và xử lý đăng nhập dùng chung."""

    def _build_login_ui(self, parent_frame):
        """Build toàn bộ UI login vào parent_frame.
        
        Subclass phải set self.colors, self._captcha_key, self._is_destroyed trước khi gọi.
        """
        c = self.colors

        # ── Title area ───────────────────────────
        title_frame = ctk.CTkFrame(parent_frame, fg_color=c["accent"], height=64, corner_radius=0)
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
        card = ctk.CTkFrame(parent_frame, fg_color=c["bg_secondary"], corner_radius=12)
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

        # Password frame — entry + toggle button
        pw_frame = ctk.CTkFrame(card, fg_color="transparent")
        pw_frame.pack(fill="x", padx=20)

        self._pw_show = False  # Track show/hide state

        self._pw_entry = ctk.CTkEntry(
            pw_frame, show="●", height=36,
            font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=c["input_bg"], border_color=c["border"],
            text_color=c["text_primary"],
        )
        self._pw_entry.pack(side="left", fill="x", expand=True)

        self._pw_toggle_btn = ctk.CTkButton(
            pw_frame, text="👁", width=36, height=36,
            font=("Segoe UI", 14),
            fg_color=c["bg_tertiary"], hover_color=c["border"],
            text_color=c["text_primary"], corner_radius=6,
            command=self._toggle_password,
        )
        self._pw_toggle_btn.pack(side="left", padx=(4, 0))

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
        self._pw_entry.bind("<Return>", lambda e: self._captcha_entry.focus())

        # Status
        self._status = ctk.CTkLabel(
            card, text="",
            font=FONTS.get("caption", ("Segoe UI", 11)),
            text_color=c["text_muted"],
        )
        self._status.pack(pady=(0, 12))

        # ── Account management ─────────────────────
        mgmt_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
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

    # ── Password toggle ──────────────────────────────────

    def _toggle_password(self):
        """Toggle show/hide mật khẩu."""
        self._pw_show = not self._pw_show
        if self._pw_show:
            self._pw_entry.configure(show="")
            self._pw_toggle_btn.configure(text="🔒")
        else:
            self._pw_entry.configure(show="●")
            self._pw_toggle_btn.configure(text="👁")

    # ── Account helpers ──────────────────────────────────

    def _on_mst_select(self, choice: str):
        mst = choice.split(" - ")[0].strip()
        pw = self._account_service.get_password(mst)
        if pw:
            self._pw_entry.delete(0, "end")
            self._pw_entry.insert(0, pw)

    def _get_current_mst(self) -> str:
        return self._mst_combo.get().split(" - ")[0].strip()

    def _load_accounts(self):
        accounts = self._account_service.get_all_accounts()
        values = [f"{a.mst} - {a.ten_cty}" if a.ten_cty else a.mst for a in accounts]
        self._mst_combo.configure(values=values)
        if values:
            self._mst_combo.set(values[0])
            self._on_mst_select(values[0])

    def _add_account_dialog(self):
        from app.ui.components.dialog import InputDialog

        parent_widget = self  # works for both CTk and CTkToplevel

        def _on_submit(value):
            parts = value.split(",")
            mst = parts[0].strip()
            ten = parts[1].strip() if len(parts) > 1 else ""
            pw = parts[2].strip() if len(parts) > 2 else ""
            if mst:
                self._account_service.add_account(mst, pw, ten)
                self._load_accounts()
                try:
                    show_toast(parent_widget, f"Đã thêm: {mst}", "success")
                except Exception:
                    pass

        InputDialog(
            parent_widget, title="Thêm tài khoản",
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
        self._account_service.delete_account(mst)
        self._load_accounts()
        try:
            show_toast(self, f"Đã xóa: {mst}", "info")
        except Exception:
            pass

    # ── CAPTCHA ──────────────────────────────────────────

    def _load_captcha(self):
        if self._is_destroyed:
            return
        self._status.configure(text="Đang lấy captcha...", text_color=self.colors["text_muted"])
        self._captcha_entry.delete(0, "end")

        def _fetch():
            result = self._auth_service.get_captcha()
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
                display_ok = False

                if getattr(result, 'content_type', '') == 'svg':
                    svg_content = result.image_bytes.decode("utf-8", errors="replace")
                    solved_text = _solve_svg_captcha(svg_content)

                    # Try tksvg native display first
                    display_ok = self._show_captcha_svg_native(result.image_bytes)

                    if not display_ok:
                        # Fall back to PIL rendering
                        img = _render_svg_to_pil(result.image_bytes, width=200, height=70)
                        if img:
                            ctk_img = ctk.CTkImage(
                                light_image=img, dark_image=img,
                                size=(160, 50)
                            )
                            self._captcha_label.configure(image=ctk_img, text="")
                            self._captcha_ctk_img = ctk_img  # Keep reference
                            display_ok = True

                    if not display_ok:
                        # Show text fallback
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
                    # PNG/JPEG captcha
                    img = Image.open(BytesIO(result.image_bytes))
                    if img:
                        ctk_img = ctk.CTkImage(
                            light_image=img, dark_image=img,
                            size=(160, 50)
                        )
                        self._captcha_label.configure(image=ctk_img, text="")
                        self._captcha_ctk_img = ctk_img  # Keep reference
                        display_ok = True

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

    def _show_captcha_svg_native(self, svg_bytes: bytes) -> bool:
        """Hiển thị SVG captcha qua tksvg (nếu có cài)."""
        try:
            import tksvg
            svg_data = svg_bytes.decode("utf-8")
            photo = tksvg.SvgImage(data=svg_data, scaletowidth=160, scaletoheight=50)
            self._captcha_photo = photo  # Keep reference

            try:
                width = photo.width()
                height = photo.height()
                if width > 0 and height > 0:
                    temp_canvas = tk.Canvas(self, width=width, height=height, bg="white", highlightthickness=0)
                    temp_canvas.create_image(0, 0, anchor="nw", image=photo)
                    temp_canvas.update_idletasks()

                    try:
                        import io
                        ps_data = temp_canvas.postscript(colormode='color')
                        pil_img = Image.open(io.BytesIO(ps_data.encode('utf-8')))
                        pil_img = pil_img.resize((160, 50), Image.LANCZOS)
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 50))
                        self._captcha_label.configure(image=ctk_img, text="")
                        self._captcha_ctk_img = ctk_img
                        temp_canvas.destroy()
                        return True
                    except Exception:
                        pass
                    temp_canvas.destroy()
            except Exception:
                pass

            self._captcha_label.configure(image=photo, text="")
            return True
        except ImportError:
            logger.debug("tksvg not installed")
        except Exception as e:
            logger.debug(f"SVG native display failed: {e}")
        return False

    # ── LOGIN ────────────────────────────────────────────

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

        logger.info(f"Login attempt: MST={mst}, captcha_key={self._captcha_key[:20]}...")

        def _login_thread():
            result = self._auth_service.login(mst, password, captcha, self._captcha_key)
            logger.info(f"Login result: success={result.success}, error={result.error_msg}, token_len={len(result.token) if result.token else 0}")
            if not self._is_destroyed:
                self.after(0, lambda: self._on_login_result(result, mst, password))

        threading.Thread(target=_login_thread, daemon=True).start()

    def _on_login_result(self, result, mst, password):
        """Xử lý kết quả đăng nhập — subclass override nếu cần."""
        if self._is_destroyed:
            return
        self._login_btn.configure(state="normal", text="Đăng nhập")

        if result.success:
            # Lưu password nếu chưa có
            if not self._account_service.has_password(mst):
                self._account_service.add_account(mst, password)
            self._status.configure(text="Đăng nhập thành công!", text_color=self.colors["success"])
            self._handle_login_success(mst, result.token)
        else:
            err = result.error_msg or "Đăng nhập thất bại"
            self._status.configure(text=f"Lỗi: {err}", text_color=self.colors["error"])
            logger.warning(f"Login failed: {err}")
            self._load_captcha()

    def _handle_login_success(self, mst: str, token: str):
        """Override trong subclass để xử lý sau login thành công."""
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════
# STANDALONE LOGIN — Dùng khi khởi động app (trước MainWindow)
# ══════════════════════════════════════════════════════════════

def show_login_and_wait() -> dict | None:
    """Hiện popup đăng nhập standalone. Trả dict {mst, token} nếu OK, None nếu cancel.
    
    Flow:
    - Tạo hidden CTk root (sẽ destroy trước khi MainWindow tạo root mới)
    - Mở LoginToplevel trên root đó
    - mainloop() chạy cho đến khi login thành công hoặc user đóng
    - Trả kết quả
    """
    import customtkinter as ctk

    # Hidden root — chỉ để làm parent cho Toplevel
    root = ctk.CTk()
    root.withdraw()  # Ẩn hoàn toàn
    root.overrideredirect(True)
    root.geometry("0x0+0+0")

    login_result = {"success": False, "mst": "", "token": ""}

    class _StartupLogin(ctk.CTkToplevel, _LoginMixin):
        """Popup đăng nhập dùng khi khởi động app."""

        def __init__(self, parent):
            super().__init__(parent)
            self.colors = get_colors()
            self._captcha_key = ""
            self._is_destroyed = False

            # Init services
            from app.models.api_client import APIClient
            from app.models.credential_store import CredentialStore
            from app.models.db_handler import DBHandler
            from app.services.auth_service import AuthService
            from app.services.account_service import AccountService

            self._db = DBHandler()
            self._api_client = APIClient()
            self._credential_store = CredentialStore()
            self._auth_service = AuthService(self._api_client, self._credential_store)
            self._account_service = AccountService(self._db, self._credential_store)

            # Window config
            self.title("Đăng nhập — Tool HDDT v2")
            self.geometry("440x520")
            self.resizable(False, False)
            self.configure(fg_color=self.colors["bg_primary"])

            # Center on screen
            self.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw - 440) // 2
            y = (sh - 520) // 2
            self.geometry(f"440x520+{x}+{y}")

            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(500, lambda: self.attributes("-topmost", False))

            self.protocol("WM_DELETE_WINDOW", self._on_close)
            self.grab_set()

            # Build UI
            self._build_login_ui(self)
            self._load_accounts()

            # Auto-load captcha
            self.after(300, self._load_captcha)

        def _handle_login_success(self, mst: str, token: str):
            login_result["success"] = True
            login_result["mst"] = mst
            login_result["token"] = token
            self.after(500, self._close)

        def _close(self):
            self._is_destroyed = True
            try:
                self._api_client.close()
            except Exception:
                pass
            try:
                self.grab_release()
            except Exception:
                pass
            root.quit()  # Kết thúc mainloop

        def _on_close(self):
            """User đóng window = thoát app."""
            login_result["success"] = False
            self._is_destroyed = True
            try:
                self._api_client.close()
            except Exception:
                pass
            try:
                self.grab_release()
            except Exception:
                pass
            root.quit()

    # Mở popup
    popup = _StartupLogin(root)
    root.mainloop()

    # Cleanup root hoàn toàn trước khi MainWindow tạo root mới
    try:
        popup.destroy()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass

    if login_result["success"]:
        return {"mst": login_result["mst"], "token": login_result["token"]}
    return None


# ══════════════════════════════════════════════════════════════
# LOGIN POPUP — Dùng khi re-login từ MainWindow
# ══════════════════════════════════════════════════════════════

class LoginPopup(ctk.CTkToplevel, _LoginMixin):
    """Popup đăng nhập cổng thuế — dùng khi re-login từ MainWindow."""

    def __init__(self, parent, main_window, mandatory: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        self.main = main_window
        self.colors = get_colors()
        self._captcha_key = ""
        self._is_destroyed = False
        self._mandatory = mandatory

        # Sử dụng services từ main_window
        self._auth_service = self.main.auth_service
        self._account_service = self.main.account_service

        # ── Window config ─────────────────────
        self.title("Đăng nhập Cổng Thuế")
        self.geometry("440x520")
        self.resizable(False, False)
        self.configure(fg_color=self.colors["bg_primary"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # Prevent closing while logging in
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_login_ui(self)
        self._load_accounts()

        # Center on parent
        self._center()

        # Auto-load captcha
        self.after(300, self._load_captcha)

    def _handle_login_success(self, mst: str, token: str):
        """Callback to main window, then close popup."""
        self.main.on_login_success(mst)
        self.after(500, self._close_popup)

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
        if self._mandatory:
            # In mandatory mode, closing popup = exit app
            import sys
            try:
                self.grab_release()
            except Exception:
                pass
            self._is_destroyed = True
            self.main.destroy()
            return

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
