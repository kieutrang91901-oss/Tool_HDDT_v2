"""
Dialog — Các loại dialog xác nhận, nhập liệu.
"""
import customtkinter as ctk
from config.theme import get_colors, FONTS


class ConfirmDialog(ctk.CTkToplevel):
    """Dialog xác nhận Yes/No."""

    def __init__(self, parent, title: str, message: str, on_confirm=None, on_cancel=None):
        super().__init__(parent)
        colors = get_colors()

        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=colors["bg_primary"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._result = False
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        # Tính toán height dựa trên số dòng message
        line_count = message.count("\n") + 1
        dialog_h = max(180, min(500, 80 + line_count * 20 + 60))
        dialog_w = 480
        self.geometry(f"{dialog_w}x{dialog_h}")

        # Message
        ctk.CTkLabel(
            self, text=message,
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=colors["text_primary"],
            wraplength=dialog_w - 40, justify="left",
            anchor="nw",
        ).pack(padx=20, pady=(24, 16), fill="both", expand=True)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 20), fill="x")

        ctk.CTkButton(
            btn_frame, text="Hủy", width=100,
            fg_color=colors["bg_tertiary"], hover_color=colors["border"],
            text_color=colors["text_primary"],
            command=self._cancel,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame, text="Xác nhận", width=100,
            fg_color=colors["accent"], hover_color=colors["accent_hover"],
            command=self._confirm,
        ).pack(side="right")

        self._center(dialog_w, dialog_h)

    def _confirm(self):
        self._result = True
        if self._on_confirm:
            self._on_confirm()
        self.destroy()

    def _cancel(self):
        self._result = False
        if self._on_cancel:
            self._on_cancel()
        self.destroy()

    def _center(self, w=400, h=180):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


class InputDialog(ctk.CTkToplevel):
    """Dialog nhập liệu 1 trường."""

    def __init__(self, parent, title: str, label: str, default: str = "", on_submit=None):
        super().__init__(parent)
        colors = get_colors()

        self.title(title)
        self.geometry("400x180")
        self.resizable(False, False)
        self.configure(fg_color=colors["bg_primary"])
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._on_submit = on_submit

        # Label
        ctk.CTkLabel(
            self, text=label,
            font=FONTS.get("body", ("Segoe UI", 13)),
            text_color=colors["text_primary"],
        ).pack(padx=20, pady=(20, 4), anchor="w")

        # Entry
        self._entry = ctk.CTkEntry(
            self, font=FONTS.get("body", ("Segoe UI", 13)),
            fg_color=colors["input_bg"], border_color=colors["border"],
            text_color=colors["text_primary"],
        )
        self._entry.pack(padx=20, fill="x")
        self._entry.insert(0, default)
        self._entry.focus()
        self._entry.bind("<Return>", lambda e: self._submit())

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=16, fill="x")

        ctk.CTkButton(
            btn_frame, text="Hủy", width=80,
            fg_color=colors["bg_tertiary"], hover_color=colors["border"],
            text_color=colors["text_primary"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame, text="OK", width=80,
            fg_color=colors["accent"], hover_color=colors["accent_hover"],
            command=self._submit,
        ).pack(side="right")

        self._center()

    def _submit(self):
        value = self._entry.get().strip()
        if self._on_submit and value:
            self._on_submit(value)
        self.destroy()

    def _center(self):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{x}+{y}")
