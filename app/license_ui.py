"""
license_ui.py — Giao diện đăng ký thiết bị & thông báo quyền sử dụng

Nguyên tắc minh bạch:
- Hiển thị rõ thông tin nào được gửi lên server.
- KHÔNG gửi file học sinh, dữ liệu hạnh kiểm, điểm số.
- Chỉ gửi: họ tên, đơn vị/trường, tên máy, UUID ngẫu nhiên.
"""

from __future__ import annotations

import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable

# Tái sử dụng design system từ main.py
_WIN = sys.platform.startswith("win")

# --- Palette (tái sử dụng từ main.py) ---
C_BG          = "#F0F4F8"
C_CARD        = "#FFFFFF"
C_CARD_ALT    = "#F8FAFC"
C_BORDER      = "#D1D9E6"
C_BORDER_FOCUS= "#2563EB"
C_TEXT        = "#0F172A"
C_TEXT_BODY   = "#334155"
C_TEXT_MUTED  = "#64748B"
C_TEXT_LIGHT  = "#94A3B8"
C_PRIMARY     = "#1E3A5F"
C_BLUE        = "#2563EB"
C_BLUE_HOVER  = "#1D4ED8"
C_SUCCESS     = "#059669"
C_SUCCESS_HOVER = "#047857"
C_DANGER      = "#DC2626"
C_GOLD        = "#92400E"
C_GOLD_BG     = "#FFFBEB"
C_GOLD_BORDER = "#FCD34D"
C_WARN_BG     = "#FFFBEB"
C_WARN_BORDER = "#FDE68A"
C_WARN_TEXT   = "#92400E"

# --- Typography ---
FONT_HEAD    = ("Segoe UI", 16, "bold") if _WIN else ("Helvetica", 16, "bold")
FONT_TITLE   = ("Segoe UI", 13, "bold") if _WIN else ("Helvetica", 13, "bold")
FONT_BODY    = ("Segoe UI", 10)         if _WIN else ("Helvetica", 10)
FONT_BODY_B  = ("Segoe UI", 10, "bold") if _WIN else ("Helvetica", 10, "bold")
FONT_SMALL   = ("Segoe UI", 9)          if _WIN else ("Helvetica", 9)
FONT_SMALL_I = ("Segoe UI", 9, "italic") if _WIN else ("Helvetica", 9, "italic")
FONT_TINY    = ("Segoe UI", 8)          if _WIN else ("Helvetica", 8)


class RegistrationDialog(tk.Toplevel):
    """
    Cửa sổ đăng ký thiết bị — hiện lần đầu mở ứng dụng.
    
    Người dùng tự nhập: họ tên, đơn vị/trường (tùy chọn).
    Hiển thị thông báo minh bạch về dữ liệu được gửi.
    """

    def __init__(self, parent: Optional[tk.Tk] = None,
                 on_register: Optional[Callable] = None):
        super().__init__(parent)
        self.on_register = on_register
        self.result = None  # (user_name, organization) hoặc None nếu hủy

        self.title("Đăng ký thiết bị")
        self.configure(bg=C_BG)
        self.resizable(False, False)

        # Kích thước và căn giữa
        w, h = 520, 560
        self.geometry(f"{w}x{h}")
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 40)}")
        except Exception:
            pass

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self._build_ui()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=C_PRIMARY, padx=20, pady=0)
        header.pack(fill="x")

        header_inner = tk.Frame(header, bg=C_PRIMARY)
        header_inner.pack(fill="x", pady=16)

        tk.Label(
            header_inner,
            text="📋  Đăng ký thiết bị",
            font=FONT_HEAD,
            fg="#FFFFFF",
            bg=C_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            header_inner,
            text="Đăng ký thiết bị để sử dụng ứng dụng Tổng hợp Hạnh kiểm",
            font=FONT_SMALL,
            fg="#93C5FD",
            bg=C_PRIMARY,
        ).pack(anchor="w", pady=(4, 0))

        # Body
        body = tk.Frame(self, bg=C_BG, padx=24, pady=20)
        body.pack(fill="both", expand=True)

        # Thông báo minh bạch
        notice_frame = tk.Frame(body, bg="#EFF6FF", bd=1, relief="solid",
                                highlightbackground="#BFDBFE", highlightthickness=1)
        notice_frame.pack(fill="x", pady=(0, 16))

        notice_inner = tk.Frame(notice_frame, bg="#EFF6FF", padx=14, pady=12)
        notice_inner.pack(fill="x")

        tk.Label(
            notice_inner,
            text="ℹ️  Thông tin gửi lên chỉ để quản lý quyền sử dụng",
            font=FONT_BODY_B,
            fg="#1E40AF",
            bg="#EFF6FF",
        ).pack(anchor="w")

        tk.Label(
            notice_inner,
            text=(
                "• Chỉ gửi: họ tên, đơn vị/trường, tên máy tính, mã thiết bị ngẫu nhiên.\n"
                "• KHÔNG gửi: file học sinh, bảng điểm, dữ liệu hạnh kiểm, mật khẩu.\n"
                "• Dữ liệu tổng hợp hạnh kiểm luôn được xử lý hoàn toàn trên máy này."
            ),
            font=FONT_SMALL,
            fg="#334155",
            bg="#EFF6FF",
            justify="left",
            wraplength=440,
        ).pack(anchor="w", pady=(6, 0))

        # Card nhập thông tin
        card = tk.Frame(body, bg=C_CARD, bd=1, relief="solid",
                       highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 16))

        card_inner = tk.Frame(card, bg=C_CARD, padx=16, pady=16)
        card_inner.pack(fill="x")

        # Họ tên (bắt buộc)
        tk.Label(
            card_inner, text="Họ và tên *", font=FONT_BODY_B,
            fg=C_TEXT, bg=C_CARD,
        ).pack(anchor="w", pady=(0, 4))

        self.name_var = tk.StringVar()
        name_entry = tk.Entry(
            card_inner,
            textvariable=self.name_var,
            font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT,
            insertbackground=C_BLUE,
            relief="solid", bd=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_BORDER_FOCUS,
            highlightthickness=1,
        )
        name_entry.pack(fill="x", ipady=6, pady=(0, 12))
        name_entry.focus_set()

        # Đơn vị / trường (tùy chọn)
        tk.Label(
            card_inner, text="Đơn vị / trường (tùy chọn)", font=FONT_BODY_B,
            fg=C_TEXT, bg=C_CARD,
        ).pack(anchor="w", pady=(0, 4))

        self.org_var = tk.StringVar()
        tk.Entry(
            card_inner,
            textvariable=self.org_var,
            font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT,
            insertbackground=C_BLUE,
            relief="solid", bd=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_BORDER_FOCUS,
            highlightthickness=1,
        ).pack(fill="x", ipady=6, pady=(0, 12))

        # Tên máy tính (chỉ đọc)
        from app.license_client import get_machine_name
        machine = get_machine_name()

        tk.Label(
            card_inner, text="Tên máy tính (tự động)", font=FONT_BODY_B,
            fg=C_TEXT_MUTED, bg=C_CARD,
        ).pack(anchor="w", pady=(0, 4))

        machine_entry = tk.Entry(
            card_inner, font=FONT_BODY,
            bg="#F1F5F9", fg=C_TEXT_MUTED,
            relief="solid", bd=1,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            state="normal",
        )
        machine_entry.insert(0, machine)
        machine_entry.configure(state="readonly")
        machine_entry.pack(fill="x", ipady=6)

        # Nút hành động
        btn_row = tk.Frame(body, bg=C_BG)
        btn_row.pack(fill="x", pady=(0, 0))

        # Nút Đăng ký
        self.btn_register = tk.Button(
            btn_row,
            text="✓  Đăng ký thiết bị",
            font=FONT_BODY_B,
            bg=C_BLUE, fg="#FFFFFF",
            activebackground=C_BLUE_HOVER,
            activeforeground="#FFFFFF",
            relief="flat", bd=0,
            cursor="hand2",
            padx=20, pady=10,
            command=self._on_register,
        )
        self.btn_register.pack(side="right", padx=(8, 0))
        self.btn_register.bind("<Enter>",
                               lambda _: self.btn_register.configure(bg=C_BLUE_HOVER))
        self.btn_register.bind("<Leave>",
                               lambda _: self.btn_register.configure(bg=C_BLUE))

        # Nút Hủy
        btn_cancel = tk.Button(
            btn_row,
            text="Thoát",
            font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT_BODY,
            activebackground=C_BORDER,
            relief="flat", bd=1,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            cursor="hand2",
            padx=16, pady=10,
            command=self._on_cancel,
        )
        btn_cancel.pack(side="right")

    def _on_register(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning(
                "Chưa nhập họ tên",
                "Vui lòng nhập họ và tên để đăng ký thiết bị.",
                parent=self,
            )
            return

        org = self.org_var.get().strip()

        # Xác nhận
        confirm = messagebox.askyesno(
            "Xác nhận đăng ký",
            f"Bạn muốn đăng ký thiết bị với thông tin sau?\n\n"
            f"• Họ tên: {name}\n"
            f"• Đơn vị: {org or '(không nhập)'}\n\n"
            "Thông tin này chỉ dùng để quản lý quyền sử dụng ứng dụng.\n"
            "Không có dữ liệu học sinh hoặc điểm số nào được gửi đi.",
            parent=self,
        )

        if not confirm:
            return

        self.btn_register.configure(
            state="disabled",
            text="⏳  Đang đăng ký...",
            bg="#6D28D9",
        )
        self.update()

        # Gọi đăng ký
        from app.license_client import register_device, generate_device_uuid
        device_uuid = generate_device_uuid()
        success, msg = register_device(name, org, device_uuid)

        if success:
            self.result = (name, org, device_uuid)
            messagebox.showinfo(
                "Đăng ký thành công",
                "Thiết bị đã được đăng ký thành công!\n\n"
                "Trạng thái hiện tại: Chờ duyệt\n"
                "Bạn vẫn có thể sử dụng ứng dụng trong thời gian chờ duyệt.\n\n"
                "Khi quản trị viên duyệt, thiết bị sẽ được kích hoạt đầy đủ.",
                parent=self,
            )
            if self.on_register:
                self.on_register(name, org, device_uuid)
            self.destroy()
        else:
            self.btn_register.configure(
                state="normal",
                text="✓  Đăng ký thiết bị",
                bg=C_BLUE,
            )
            messagebox.showerror(
                "Đăng ký không thành công",
                f"Không thể đăng ký thiết bị:\n{msg}\n\n"
                "Vui lòng kiểm tra kết nối Internet và thử lại.",
                parent=self,
            )

    def _on_cancel(self):
        self.result = None
        self.destroy()


class LicenseStatusDialog(tk.Toplevel):
    """
    Cửa sổ thông báo trạng thái quyền sử dụng.
    Dùng khi quyền bị thu hồi, tạm ngưng, hoặc hết hạn offline.
    """

    def __init__(self, parent: Optional[tk.Tk] = None,
                 title_text: str = "Thông báo quyền sử dụng",
                 message: str = "",
                 status: str = "",
                 allow_continue: bool = False,
                 on_retry: Optional[Callable] = None):
        super().__init__(parent)
        self.allow_continue = allow_continue
        self.on_retry = on_retry
        self.user_choice = None  # "continue", "retry", "exit"

        self.title(title_text)
        self.configure(bg=C_BG)
        self.resizable(False, False)

        w, h = 480, 340
        self.geometry(f"{w}x{h}")
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 40)}")
        except Exception:
            pass

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

        self._build_ui(title_text, message, status)

    def _build_ui(self, title_text: str, message: str, status: str):
        # Header
        is_error = status in ("DA_THU_HOI", "TAM_NGUNG", "HET_HAN")
        header_bg = C_DANGER if is_error else C_PRIMARY

        header = tk.Frame(self, bg=header_bg, padx=20, pady=0)
        header.pack(fill="x")

        header_inner = tk.Frame(header, bg=header_bg)
        header_inner.pack(fill="x", pady=14)

        icon = "⚠️" if is_error else "ℹ️"
        tk.Label(
            header_inner,
            text=f"{icon}  {title_text}",
            font=FONT_TITLE,
            fg="#FFFFFF",
            bg=header_bg,
        ).pack(anchor="w")

        # Body
        body = tk.Frame(self, bg=C_BG, padx=24, pady=20)
        body.pack(fill="both", expand=True)

        # Message card
        msg_bg = "#FEF2F2" if is_error else "#EFF6FF"
        msg_border = "#FECACA" if is_error else "#BFDBFE"
        msg_fg = "#991B1B" if is_error else "#1E40AF"

        msg_frame = tk.Frame(body, bg=msg_bg, bd=1, relief="solid",
                            highlightbackground=msg_border, highlightthickness=1)
        msg_frame.pack(fill="both", expand=True, pady=(0, 16))

        msg_inner = tk.Frame(msg_frame, bg=msg_bg, padx=16, pady=16)
        msg_inner.pack(fill="both", expand=True)

        tk.Label(
            msg_inner,
            text=message,
            font=FONT_BODY,
            fg=msg_fg,
            bg=msg_bg,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", fill="both", expand=True)

        # Buttons
        btn_row = tk.Frame(body, bg=C_BG)
        btn_row.pack(fill="x")

        # Nút Thoát
        btn_exit = tk.Button(
            btn_row,
            text="Đóng ứng dụng",
            font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT_BODY,
            activebackground=C_BORDER,
            relief="flat", bd=1,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            cursor="hand2",
            padx=16, pady=9,
            command=self._on_exit,
        )
        btn_exit.pack(side="right", padx=(8, 0))

        # Nút Thử lại
        if self.on_retry:
            btn_retry = tk.Button(
                btn_row,
                text="🔄  Thử lại",
                font=FONT_BODY_B,
                bg=C_BLUE, fg="#FFFFFF",
                activebackground=C_BLUE_HOVER,
                activeforeground="#FFFFFF",
                relief="flat", bd=0,
                cursor="hand2",
                padx=16, pady=9,
                command=self._on_retry,
            )
            btn_retry.pack(side="right", padx=(8, 0))
            btn_retry.bind("<Enter>",
                           lambda _: btn_retry.configure(bg=C_BLUE_HOVER))
            btn_retry.bind("<Leave>",
                           lambda _: btn_retry.configure(bg=C_BLUE))

        # Nút Tiếp tục (nếu được phép)
        if self.allow_continue:
            btn_continue = tk.Button(
                btn_row,
                text="▶  Tiếp tục sử dụng",
                font=FONT_BODY_B,
                bg=C_SUCCESS, fg="#FFFFFF",
                activebackground=C_SUCCESS_HOVER,
                activeforeground="#FFFFFF",
                relief="flat", bd=0,
                cursor="hand2",
                padx=16, pady=9,
                command=self._on_continue,
            )
            btn_continue.pack(side="right")
            btn_continue.bind("<Enter>",
                              lambda _: btn_continue.configure(bg=C_SUCCESS_HOVER))
            btn_continue.bind("<Leave>",
                              lambda _: btn_continue.configure(bg=C_SUCCESS))

    def _on_continue(self):
        self.user_choice = "continue"
        self.destroy()

    def _on_retry(self):
        self.user_choice = "retry"
        if self.on_retry:
            self.on_retry()
        self.destroy()

    def _on_exit(self):
        self.user_choice = "exit"
        self.destroy()


def run_license_check_ui(root: tk.Tk) -> bool:
    """
    Chạy kiểm tra license với giao diện.
    Trả về True nếu cho phép tiếp tục, False nếu phải thoát.
    
    Luồng xử lý:
    1. Chưa đăng ký → hiện RegistrationDialog
    2. Quyền hợp lệ → return True
    3. Quyền bị thu hồi/tạm ngưng → hiện LicenseStatusDialog → return False
    4. Offline còn hạn → hiện cảnh báo nhẹ → return True
    5. Offline hết hạn → hiện LicenseStatusDialog yêu cầu kết nối
    """
    from app.license_client import (
        check_license, LicenseCache, LicenseCheckResult,
        STATUS_CHO_DUYET, STATUS_DANG_HOAT_DONG,
        STATUS_DA_THU_HOI, STATUS_TAM_NGUNG,
        get_supabase_config,
    )

    # Kiểm tra có cấu hình Supabase không
    supa_url, anon_key = get_supabase_config()
    if not supa_url or not anon_key:
        # Chưa cấu hình → cho chạy bình thường (không có license system)
        return True

    result = check_license()

    if result.need_registration:
        # Hiện form đăng ký
        dialog = RegistrationDialog(root)
        root.wait_window(dialog)

        if dialog.result is None:
            # Người dùng hủy đăng ký → thoát
            return False

        # Đăng ký xong → kiểm tra lại
        result = check_license()

    if result.allowed:
        if result.status == STATUS_CHO_DUYET:
            # Thông báo nhẹ: đang chờ duyệt
            _show_status_bar_message(root, result.message, "info")
        elif result.is_offline:
            # Thông báo nhẹ: đang offline
            _show_status_bar_message(root, result.message, "warning")
        return True
    else:
        # Không được phép — hiện dialog
        is_offline_expired = not result.is_offline and result.status not in (
            STATUS_DA_THU_HOI, STATUS_TAM_NGUNG
        )

        def retry_check():
            nonlocal result
            result = check_license()

        dialog = LicenseStatusDialog(
            root,
            title_text="Quyền sử dụng",
            message=result.message,
            status=result.status or "",
            allow_continue=False,
            on_retry=retry_check if result.is_offline else None,
        )
        root.wait_window(dialog)

        if dialog.user_choice == "continue":
            return True
        return False


def _show_status_bar_message(root: tk.Tk, message: str, level: str = "info"):
    """Gắn thanh thông báo nhỏ ở dưới cùng cửa sổ chính."""
    # Lưu message để topbar hiển thị sau khi build UI
    root._license_status_message = message
    root._license_status_level = level


class LicenseMonitor:
    """
    Giám sát quyền sử dụng theo thời gian thực (Heartbeat).
    - Chạy nền (daemon thread) mỗi 20 giây một lần.
    - Tự động kích hoạt kiểm tra ngay khi người dùng click/focus vào cửa sổ ứng dụng (<FocusIn>).
    - Ngay khi phát hiện trạng thái TAM_NGUNG hoặc DA_THU_HOI:
      -> Khóa giao diện làm việc ngay lập tức, hiển thị thông báo và thoát ứng dụng.
    """

    def __init__(self, root: tk.Tk, interval_seconds: int = 20):
        self.root = root
        self.interval = interval_seconds
        self._stop_event = threading.Event()
        self._last_check_time = 0.0
        self._check_lock = threading.Lock()
        self._is_checking = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="LicenseHeartbeatThread"
        )
        self._thread.start()

        # Bắt sự kiện khi người dùng focus vào cửa sổ chính
        try:
            self.root.bind("<FocusIn>", self._on_focus, add="+")
        except Exception:
            pass

    def stop(self):
        self._stop_event.set()

    def _on_focus(self, event=None):
        if event and getattr(event, "widget", None) != self.root:
            return
        now = time.time()
        # Throttling: tối thiểu 6 giây giữa các lần check focus
        if now - self._last_check_time >= 6 and not self._is_checking:
            t = threading.Thread(target=self._check_once, daemon=True)
            t.start()

    def _heartbeat_loop(self):
        # Đợi 5 giây sau khi mở app mới bắt đầu vòng lặp (vì startup đã check 1 lần)
        if self._stop_event.wait(timeout=5):
            return

        while not self._stop_event.is_set():
            self._check_once()
            if self._stop_event.wait(timeout=self.interval):
                break

    def _check_once(self):
        with self._check_lock:
            if self._stop_event.is_set():
                return
            self._is_checking = True
            self._last_check_time = time.time()

        try:
            from app.license_client import check_license
            result = check_license()
            if not result.allowed:
                self.stop()
                self.root.after(0, lambda: self._handle_lockout(result))
        except Exception:
            pass
        finally:
            self._is_checking = False

    def _handle_lockout(self, result):
        """Khóa giao diện và hiển thị thông báo thu hồi / tạm ngưng."""
        try:
            # Ẩn cửa sổ chính ngay lập tức để người dùng không thể thao tác tiếp
            self.root.withdraw()
            dialog = LicenseStatusDialog(
                None,
                title_text="Quyền sử dụng",
                message=result.message or "Quyền sử dụng ứng dụng tạm thời bị tạm ngưng hoặc thu hồi.\nVui lòng liên hệ TB.",
                status=result.status or "DA_THU_HOI",
                allow_continue=False,
            )
            dialog.wait_window()
        except Exception:
            from tkinter import messagebox
            messagebox.showerror(
                "Quyền sử dụng",
                result.message or "Quyền sử dụng ứng dụng không còn hiệu lực.\nVui lòng liên hệ TB."
            )
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass
            import os
            os._exit(0)


def start_license_monitor(root: tk.Tk) -> LicenseMonitor:
    """Khởi động bộ giám sát bản quyền thời gian thực."""
    monitor = LicenseMonitor(root, interval_seconds=20)
    monitor.start()
    return monitor

