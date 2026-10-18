"""
admin_dashboard.py — Công cụ quản trị quyền sử dụng từ xa

Chức năng:
- Đăng nhập quản trị bằng Supabase Auth (email/password)
- Xem danh sách thiết bị: người dùng, tên máy, đơn vị, trạng thái, lần dùng gần nhất
- Tìm kiếm theo tên người dùng hoặc tên máy
- Duyệt / Tạm ngưng / Thu hồi / Kích hoạt lại thiết bị
- Xem lịch sử thao tác
- Xác nhận rõ ràng trước khi thay đổi trạng thái

An toàn:
- KHÔNG dùng SERVICE_ROLE_KEY
- Dùng Supabase Auth + RLS/role
- Chỉ dùng SUPABASE_URL + SUPABASE_ANON_KEY + access_token sau đăng nhập
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import ssl
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

import tkinter as tk
from tkinter import messagebox, ttk

# ---------------------------------------------------------------------------
# Design System — cùng phong cách ứng dụng chính
# ---------------------------------------------------------------------------
_WIN = sys.platform.startswith("win")

C_BG          = "#F0F4F8"
C_BG_STRIPE   = "#E8EEF4"
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
C_TEAL        = "#0F766E"
C_TEAL_HOVER  = "#115E59"
C_SUCCESS     = "#059669"
C_SUCCESS_HOVER = "#047857"
C_DANGER      = "#DC2626"
C_DANGER_HOVER= "#B91C1C"
C_WARN        = "#D97706"
C_WARN_HOVER  = "#B45309"
C_GOLD        = "#92400E"
C_GOLD_BG     = "#FFFBEB"
C_GOLD_BORDER = "#FCD34D"
C_VIOLET      = "#7C3AED"

FONT_HEAD    = ("Segoe UI", 16, "bold") if _WIN else ("Helvetica", 16, "bold")
FONT_TITLE   = ("Segoe UI", 13, "bold") if _WIN else ("Helvetica", 13, "bold")
FONT_STEP    = ("Segoe UI", 11, "bold") if _WIN else ("Helvetica", 11, "bold")
FONT_BODY    = ("Segoe UI", 10)         if _WIN else ("Helvetica", 10)
FONT_BODY_B  = ("Segoe UI", 10, "bold") if _WIN else ("Helvetica", 10, "bold")
FONT_SMALL   = ("Segoe UI", 9)          if _WIN else ("Helvetica", 9)
FONT_SMALL_I = ("Segoe UI", 9, "italic") if _WIN else ("Helvetica", 9, "italic")
FONT_TINY    = ("Segoe UI", 8)          if _WIN else ("Helvetica", 8)
FONT_MONO    = ("Consolas", 9)          if _WIN else ("Courier", 9)

# Trạng thái
STATUS_CHO_DUYET = "CHO_DUYET"
STATUS_DANG_HOAT_DONG = "DANG_HOAT_DONG"
STATUS_DA_THU_HOI = "DA_THU_HOI"
STATUS_TAM_NGUNG = "TAM_NGUNG"

STATUS_LABELS = {
    STATUS_CHO_DUYET: "⏳ Chờ duyệt",
    STATUS_DANG_HOAT_DONG: "✅ Đang hoạt động",
    STATUS_DA_THU_HOI: "🚫 Đã thu hồi",
    STATUS_TAM_NGUNG: "⏸️ Tạm ngưng",
}

STATUS_COLORS = {
    STATUS_CHO_DUYET: "#D97706",
    STATUS_DANG_HOAT_DONG: "#059669",
    STATUS_DA_THU_HOI: "#DC2626",
    STATUS_TAM_NGUNG: "#6B7280",
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _load_env_file() -> dict:
    env_data = {}
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".env")
    candidates.extend([
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ])
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            env_data[key.strip()] = value.strip().strip('"').strip("'")
            except Exception:
                pass
            break
    return env_data


def get_config() -> Tuple[Optional[str], Optional[str]]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        env_data = _load_env_file()
        url = url or env_data.get("SUPABASE_URL")
        key = key or env_data.get("SUPABASE_ANON_KEY")
    if url and key:
        url = url.rstrip("/")
        if url.endswith("/rest/v1"):
            url = url[:-len("/rest/v1")]
        return url, key
    return None, None


def _make_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    body: Optional[dict] = None,
    timeout: int = 15,
) -> Tuple[int, Optional[dict]]:
    if headers is None:
        headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp_data = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(resp_data) if resp_data.strip() else None
            except json.JSONDecodeError:
                return resp.status, None
    except urllib.error.HTTPError as e:
        resp_data = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(resp_data) if resp_data.strip() else {"error": str(e)}
        except json.JSONDecodeError:
            return e.code, {"error": resp_data}
    except Exception:
        return 0, None


# ---------------------------------------------------------------------------
# Supabase Auth
# ---------------------------------------------------------------------------

class SupabaseAuth:
    def __init__(self, supa_url: str, anon_key: str):
        self.supa_url = supa_url
        self.anon_key = anon_key
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_email: Optional[str] = None

    def login(self, email: str, password: str) -> Tuple[bool, str]:
        url = f"{self.supa_url}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }
        body = {"email": email, "password": password}
        status, data = _make_request(url, "POST", headers, body)

        if status == 200 and data:
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            user = data.get("user", {})
            self.user_email = user.get("email", email)
            return True, "Đăng nhập thành công"
        elif data:
            msg = data.get("error_description") or data.get("msg") or data.get("error", "")
            if "Invalid login" in str(msg) or "invalid" in str(msg).lower():
                return False, "Email hoặc mật khẩu không đúng."
            return False, f"Lỗi đăng nhập: {msg}"
        return False, "Không thể kết nối đến server. Kiểm tra Internet."

    def auth_headers(self) -> dict:
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }


# ---------------------------------------------------------------------------
# Admin API
# ---------------------------------------------------------------------------

class AdminAPI:
    def __init__(self, auth: SupabaseAuth):
        self.auth = auth
        self.supa_url = auth.supa_url

    def list_devices(self, search: str = "") -> Tuple[bool, list]:
        url = (
            f"{self.supa_url}/rest/v1/devices"
            f"?select=*&order=created_at.desc"
        )
        if search:
            search_encoded = urllib.parse.quote(f"%{search}%")
            url += f"&or=(user_name.ilike.{search_encoded},machine_name.ilike.{search_encoded},organization.ilike.{search_encoded})"

        status, data = _make_request(url, "GET", self.auth.auth_headers())
        if status == 200 and isinstance(data, list):
            return True, data
        return False, []

    def update_device_status(
        self, device_uuid: str, new_status: str, note: str = ""
    ) -> Tuple[bool, str]:
        url = (
            f"{self.supa_url}/rest/v1/devices"
            f"?device_uuid=eq.{urllib.parse.quote(device_uuid)}"
        )
        body = {"status": new_status, "note": note}
        if new_status == STATUS_DA_THU_HOI:
            body["revoked_at"] = datetime.now().isoformat()
        elif new_status == STATUS_DANG_HOAT_DONG:
            body["revoked_at"] = None

        status, data = _make_request(url, "PATCH", self.auth.auth_headers(), body)

        if status in (200, 204):
            # Log event
            self._log_event(device_uuid, self._status_to_event(new_status),
                           f"Thay đổi trạng thái → {new_status}. {note}".strip())
            return True, "Cập nhật thành công"
        return False, f"Lỗi cập nhật (HTTP {status})"

    def get_events(self, device_uuid: str = "", limit: int = 50) -> list:
        url = (
            f"{self.supa_url}/rest/v1/license_events"
            f"?select=*&order=created_at.desc&limit={limit}"
        )
        if device_uuid:
            url += f"&device_uuid=eq.{urllib.parse.quote(device_uuid)}"

        status, data = _make_request(url, "GET", self.auth.auth_headers())
        if status == 200 and isinstance(data, list):
            return data
        return []

    def _log_event(self, device_uuid: str, event_type: str, detail: str):
        url = f"{self.supa_url}/rest/v1/license_events"
        body = {
            "device_uuid": device_uuid,
            "event_type": event_type,
            "detail": detail,
            "admin_email": self.auth.user_email or "",
            "created_at": datetime.now().isoformat(),
        }
        _make_request(url, "POST", self.auth.auth_headers(), body)

    @staticmethod
    def _status_to_event(status: str) -> str:
        mapping = {
            STATUS_DANG_HOAT_DONG: "DUYET",
            STATUS_DA_THU_HOI: "THU_HOI",
            STATUS_TAM_NGUNG: "TAM_NGUNG",
            STATUS_CHO_DUYET: "GHI_CHU",
        }
        return mapping.get(status, "GHI_CHU")


# ---------------------------------------------------------------------------
# Modern Button (tái sử dụng)
# ---------------------------------------------------------------------------

class ModernButton(tk.Button):
    def __init__(self, master=None, bg_color=C_BLUE, hover_color=C_BLUE_HOVER,
                 text_color="#FFFFFF", font_spec=None, **kwargs):
        if font_spec is None:
            font_spec = FONT_BODY_B
        self.default_bg = bg_color
        self.hover_bg = hover_color
        self.default_fg = text_color
        padx = kwargs.pop("padx", 16)
        pady = kwargs.pop("pady", 8)
        super().__init__(
            master, bg=self.default_bg, fg=self.default_fg,
            activebackground=self.hover_bg, activeforeground=self.default_fg,
            relief="flat", bd=0, cursor="hand2", font=font_spec,
            padx=padx, pady=pady, **kwargs
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self.hover_bg)

    def _on_leave(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self.default_bg)


# ---------------------------------------------------------------------------
# Login Frame
# ---------------------------------------------------------------------------

class LoginFrame(tk.Frame):
    def __init__(self, master, on_login_success):
        super().__init__(master, bg=C_BG)
        self.on_login_success = on_login_success
        self._build()

    def _build(self):
        # Center container
        center = tk.Frame(self, bg=C_BG)
        center.place(relx=0.5, rely=0.45, anchor="center")

        # Header card
        header = tk.Frame(center, bg=C_PRIMARY, padx=30, pady=0)
        header.pack(fill="x")

        header_inner = tk.Frame(header, bg=C_PRIMARY)
        header_inner.pack(fill="x", pady=20)

        tk.Label(
            header_inner,
            text="🔐  Quản trị quyền sử dụng",
            font=FONT_HEAD, fg="#FFFFFF", bg=C_PRIMARY,
        ).pack(anchor="w")

        tk.Label(
            header_inner,
            text="Đăng nhập bằng tài khoản quản trị Supabase",
            font=FONT_SMALL, fg="#93C5FD", bg=C_PRIMARY,
        ).pack(anchor="w", pady=(4, 0))

        # Login card
        card = tk.Frame(center, bg=C_CARD, bd=1, relief="solid",
                       highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x")

        inner = tk.Frame(card, bg=C_CARD, padx=30, pady=24)
        inner.pack(fill="x")

        # Email
        tk.Label(inner, text="Email quản trị", font=FONT_BODY_B,
                fg=C_TEXT, bg=C_CARD).pack(anchor="w", pady=(0, 4))

        self.email_var = tk.StringVar()
        email_entry = tk.Entry(
            inner, textvariable=self.email_var, font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT, insertbackground=C_BLUE,
            relief="solid", bd=1, highlightbackground=C_BORDER,
            highlightcolor=C_BORDER_FOCUS, highlightthickness=1,
        )
        email_entry.pack(fill="x", ipady=6, pady=(0, 14))
        email_entry.focus_set()

        # Password
        tk.Label(inner, text="Mật khẩu", font=FONT_BODY_B,
                fg=C_TEXT, bg=C_CARD).pack(anchor="w", pady=(0, 4))

        self.pw_var = tk.StringVar()
        pw_entry = tk.Entry(
            inner, textvariable=self.pw_var, font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT, insertbackground=C_BLUE,
            relief="solid", bd=1, highlightbackground=C_BORDER,
            highlightcolor=C_BORDER_FOCUS, highlightthickness=1,
            show="●",
        )
        pw_entry.pack(fill="x", ipady=6, pady=(0, 18))
        pw_entry.bind("<Return>", lambda _: self._do_login())

        # Status label
        self.status_label = tk.Label(
            inner, text="", font=FONT_SMALL, fg=C_DANGER, bg=C_CARD,
        )
        self.status_label.pack(anchor="w", pady=(0, 10))

        # Login button
        self.btn_login = ModernButton(
            inner, text="  Đăng nhập  ",
            bg_color=C_BLUE, hover_color=C_BLUE_HOVER,
            font_spec=FONT_BODY_B, padx=24, pady=10,
            command=self._do_login,
        )
        self.btn_login.pack(fill="x")

        # Info note
        tk.Label(
            inner,
            text="ℹ️ Dùng tài khoản đã tạo trên Supabase Dashboard → Authentication",
            font=FONT_TINY, fg=C_TEXT_LIGHT, bg=C_CARD,
            wraplength=320, justify="left",
        ).pack(anchor="w", pady=(12, 0))

    def _do_login(self):
        email = self.email_var.get().strip()
        password = self.pw_var.get().strip()

        if not email or not password:
            self.status_label.configure(text="Vui lòng nhập email và mật khẩu.")
            return

        self.btn_login.configure(state="disabled", text="  Đang đăng nhập...  ")
        self.status_label.configure(text="", fg=C_TEXT_MUTED)
        self.update()

        supa_url, anon_key = get_config()
        if not supa_url or not anon_key:
            self.status_label.configure(
                text="Chưa cấu hình SUPABASE_URL và SUPABASE_ANON_KEY.\nKiểm tra file .env.",
                fg=C_DANGER,
            )
            self.btn_login.configure(state="normal", text="  Đăng nhập  ")
            return

        auth = SupabaseAuth(supa_url, anon_key)
        success, msg = auth.login(email, password)

        if success:
            self.on_login_success(auth)
        else:
            self.status_label.configure(text=msg, fg=C_DANGER)
            self.btn_login.configure(state="normal", text="  Đăng nhập  ")


# ---------------------------------------------------------------------------
# Dashboard Frame
# ---------------------------------------------------------------------------

class DashboardFrame(tk.Frame):
    def __init__(self, master, auth: SupabaseAuth, on_logout):
        super().__init__(master, bg=C_BG)
        self.auth = auth
        self.api = AdminAPI(auth)
        self.on_logout = on_logout
        self.devices = []
        self.selected_device = None

        self._build()
        self.after(100, self._load_devices)

    def _build(self):
        # Top bar
        self._build_topbar()

        # Main content (paned)
        paned = tk.PanedWindow(self, orient="horizontal", bg=C_BG,
                               sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        # Left panel: device list
        left = tk.Frame(paned, bg=C_BG)
        self._build_device_list(left)
        paned.add(left, width=640, minsize=400)

        # Right panel: detail + events
        right = tk.Frame(paned, bg=C_BG)
        self._build_detail_panel(right)
        paned.add(right, width=380, minsize=300)

    def _build_topbar(self):
        bar = tk.Frame(self, bg=C_PRIMARY, padx=16, pady=0)
        bar.pack(fill="x")

        inner = tk.Frame(bar, bg=C_PRIMARY)
        inner.pack(fill="x", pady=12)

        # Left: title
        left = tk.Frame(inner, bg=C_PRIMARY)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left,
            text="🛡️  Quản trị quyền sử dụng",
            font=FONT_HEAD, fg="#FFFFFF", bg=C_PRIMARY,
        ).pack(side="left")

        # Right: user info + logout
        right = tk.Frame(inner, bg=C_PRIMARY)
        right.pack(side="right")

        tk.Label(
            right,
            text=f"👤 {self.auth.user_email}",
            font=FONT_SMALL, fg="#93C5FD", bg=C_PRIMARY,
        ).pack(side="left", padx=(0, 12))

        ModernButton(
            right, text="Đăng xuất",
            bg_color="#374151", hover_color="#4B5563",
            font_spec=FONT_SMALL, padx=12, pady=5,
            command=self.on_logout,
        ).pack(side="left")

    def _build_device_list(self, parent):
        # Search bar
        search_frame = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                               highlightbackground=C_BORDER, highlightthickness=1)
        search_frame.pack(fill="x", pady=(0, 8))

        search_inner = tk.Frame(search_frame, bg=C_CARD, padx=12, pady=10)
        search_inner.pack(fill="x")

        tk.Label(search_inner, text="🔍", font=FONT_BODY,
                bg=C_CARD).pack(side="left", padx=(0, 6))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_inner, textvariable=self.search_var, font=FONT_BODY,
            bg=C_CARD_ALT, fg=C_TEXT, insertbackground=C_BLUE,
            relief="solid", bd=1, highlightbackground=C_BORDER,
            highlightcolor=C_BORDER_FOCUS, highlightthickness=1,
        )
        search_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))
        search_entry.insert(0, "")
        search_entry.bind("<Return>", lambda _: self._load_devices())

        # Placeholder
        def _on_focus_in(_):
            pass
        search_entry.bind("<FocusIn>", _on_focus_in)

        ModernButton(
            search_inner, text="Tìm kiếm",
            bg_color=C_BLUE, hover_color=C_BLUE_HOVER,
            font_spec=FONT_SMALL, padx=12, pady=5,
            command=self._load_devices,
        ).pack(side="left", padx=(0, 4))

        ModernButton(
            search_inner, text="⟳ Tải lại",
            bg_color="#6B7280", hover_color="#4B5563",
            font_spec=FONT_SMALL, padx=12, pady=5,
            command=lambda: (self.search_var.set(""), self._load_devices()),
        ).pack(side="left")

        # Stats bar
        self.stats_frame = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                                    highlightbackground=C_BORDER, highlightthickness=1)
        self.stats_frame.pack(fill="x", pady=(0, 8))

        self.stats_inner = tk.Frame(self.stats_frame, bg=C_CARD, padx=12, pady=8)
        self.stats_inner.pack(fill="x")

        self.stats_label = tk.Label(
            self.stats_inner, text="Đang tải...", font=FONT_SMALL,
            fg=C_TEXT_MUTED, bg=C_CARD,
        )
        self.stats_label.pack(side="left")

        # Treeview
        tree_frame = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                             highlightbackground=C_BORDER, highlightthickness=1)
        tree_frame.pack(fill="both", expand=True)

        columns = ("user_name", "machine_name", "organization", "status", "last_seen")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                selectmode="browse")

        self.tree.heading("user_name", text="Họ tên")
        self.tree.heading("machine_name", text="Tên máy")
        self.tree.heading("organization", text="Đơn vị")
        self.tree.heading("status", text="Trạng thái")
        self.tree.heading("last_seen", text="Lần dùng gần nhất")

        self.tree.column("user_name", width=130, minwidth=80)
        self.tree.column("machine_name", width=120, minwidth=80)
        self.tree.column("organization", width=130, minwidth=80)
        self.tree.column("status", width=120, minwidth=80)
        self.tree.column("last_seen", width=140, minwidth=100)

        # Style treeview
        style = ttk.Style()
        style.configure("Treeview", font=FONT_BODY, rowheight=28,
                        background=C_CARD, fieldbackground=C_CARD)
        style.configure("Treeview.Heading", font=FONT_BODY_B,
                        background=C_CARD_ALT, foreground=C_TEXT)
        style.map("Treeview", background=[("selected", "#DBEAFE")])

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_device_select)

    def _build_detail_panel(self, parent):
        # Detail card
        self.detail_card = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                                    highlightbackground=C_BORDER, highlightthickness=1)
        self.detail_card.pack(fill="x", pady=(0, 8))

        self.detail_inner = tk.Frame(self.detail_card, bg=C_CARD, padx=16, pady=16)
        self.detail_inner.pack(fill="x")

        self.detail_title = tk.Label(
            self.detail_inner, text="Chọn thiết bị để xem chi tiết",
            font=FONT_TITLE, fg=C_TEXT_MUTED, bg=C_CARD,
        )
        self.detail_title.pack(anchor="w")

        self.detail_info_frame = tk.Frame(self.detail_inner, bg=C_CARD)
        self.detail_info_frame.pack(fill="x", pady=(10, 0))

        # Action buttons
        self.action_frame = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                                     highlightbackground=C_BORDER, highlightthickness=1)
        self.action_frame.pack(fill="x", pady=(0, 8))

        action_inner = tk.Frame(self.action_frame, bg=C_CARD, padx=16, pady=12)
        action_inner.pack(fill="x")

        tk.Label(action_inner, text="Thao tác", font=FONT_BODY_B,
                fg=C_TEXT, bg=C_CARD).pack(anchor="w", pady=(0, 8))

        btn_grid = tk.Frame(action_inner, bg=C_CARD)
        btn_grid.pack(fill="x")

        self.btn_approve = ModernButton(
            btn_grid, text="✓ Duyệt",
            bg_color=C_SUCCESS, hover_color=C_SUCCESS_HOVER,
            font_spec=FONT_SMALL, padx=12, pady=6,
            command=lambda: self._change_status(STATUS_DANG_HOAT_DONG),
        )
        self.btn_approve.pack(side="left", padx=(0, 6))

        self.btn_suspend = ModernButton(
            btn_grid, text="⏸ Tạm ngưng",
            bg_color=C_WARN, hover_color=C_WARN_HOVER,
            font_spec=FONT_SMALL, padx=12, pady=6,
            command=lambda: self._change_status(STATUS_TAM_NGUNG),
        )
        self.btn_suspend.pack(side="left", padx=(0, 6))

        self.btn_revoke = ModernButton(
            btn_grid, text="🚫 Thu hồi",
            bg_color=C_DANGER, hover_color=C_DANGER_HOVER,
            font_spec=FONT_SMALL, padx=12, pady=6,
            command=lambda: self._change_status(STATUS_DA_THU_HOI),
        )
        self.btn_revoke.pack(side="left", padx=(0, 6))

        self.btn_reactivate = ModernButton(
            btn_grid, text="▶ Kích hoạt lại",
            bg_color=C_TEAL, hover_color=C_TEAL_HOVER,
            font_spec=FONT_SMALL, padx=12, pady=6,
            command=lambda: self._change_status(STATUS_DANG_HOAT_DONG),
        )
        self.btn_reactivate.pack(side="left")

        # Events log
        events_card = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                              highlightbackground=C_BORDER, highlightthickness=1)
        events_card.pack(fill="both", expand=True)

        events_header = tk.Frame(events_card, bg=C_CARD, padx=16, pady=10)
        events_header.pack(fill="x")

        tk.Label(events_header, text="📋 Lịch sử thao tác", font=FONT_BODY_B,
                fg=C_TEXT, bg=C_CARD).pack(side="left")

        self.btn_load_all_events = ModernButton(
            events_header, text="Xem tất cả",
            bg_color="#6B7280", hover_color="#4B5563",
            font_spec=FONT_TINY, padx=8, pady=3,
            command=self._load_all_events,
        )
        self.btn_load_all_events.pack(side="right")

        self.events_text = tk.Text(
            events_card, height=10, bg=C_CARD, fg=C_TEXT_BODY,
            font=FONT_MONO, relief="flat", bd=0,
            padx=12, pady=8, wrap="word", state="disabled",
        )
        self.events_text.pack(fill="both", expand=True)

    # -----------------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------------

    def _load_devices(self):
        search = self.search_var.get().strip()

        def _do():
            success, data = self.api.list_devices(search)
            self.after(0, lambda: self._on_devices_loaded(success, data))

        threading.Thread(target=_do, daemon=True).start()

    def _on_devices_loaded(self, success: bool, data: list):
        if not success:
            self.stats_label.configure(text="❌ Không thể tải dữ liệu. Kiểm tra quyền quản trị.", fg=C_DANGER)
            return

        self.devices = data

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Count stats
        counts = {s: 0 for s in (STATUS_CHO_DUYET, STATUS_DANG_HOAT_DONG, STATUS_DA_THU_HOI, STATUS_TAM_NGUNG)}
        for d in data:
            s = d.get("status", "")
            if s in counts:
                counts[s] += 1

        self.stats_label.configure(
            text=(
                f"Tổng: {len(data)}  ·  "
                f"✅ {counts[STATUS_DANG_HOAT_DONG]}  ·  "
                f"⏳ {counts[STATUS_CHO_DUYET]}  ·  "
                f"⏸ {counts[STATUS_TAM_NGUNG]}  ·  "
                f"🚫 {counts[STATUS_DA_THU_HOI]}"
            ),
            fg=C_TEXT_BODY,
        )

        # Populate tree
        for i, d in enumerate(data):
            status = d.get("status", "")
            status_label = STATUS_LABELS.get(status, status)

            last_seen = d.get("last_seen_at", "")
            if last_seen:
                try:
                    dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    last_seen = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

            tag = f"row_{i}"
            self.tree.insert("", "end",
                iid=str(i),
                values=(
                    d.get("user_name", ""),
                    d.get("machine_name", ""),
                    d.get("organization", ""),
                    status_label,
                    last_seen,
                ),
                tags=(tag,),
            )

            # Color rows by status
            color = STATUS_COLORS.get(status, C_TEXT)
            self.tree.tag_configure(tag, foreground=color if status != STATUS_DANG_HOAT_DONG else C_TEXT)

    def _on_device_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return

        idx = int(selection[0])
        if idx < 0 or idx >= len(self.devices):
            return

        device = self.devices[idx]
        self.selected_device = device
        self._update_detail(device)
        self._load_device_events(device.get("device_uuid", ""))

    def _update_detail(self, device: dict):
        # Clear old info
        for w in self.detail_info_frame.winfo_children():
            w.destroy()

        status = device.get("status", "")
        self.detail_title.configure(
            text=f"{device.get('user_name', 'N/A')}",
            fg=C_TEXT,
        )

        # Info rows
        info = [
            ("Tên máy", device.get("machine_name", "")),
            ("Đơn vị", device.get("organization", "") or "(không nhập)"),
            ("Trạng thái", STATUS_LABELS.get(status, status)),
            ("Phiên bản", device.get("app_version", "")),
            ("UUID", device.get("device_uuid", "")[:12] + "..."),
            ("Đăng ký lúc", _format_dt(device.get("created_at", ""))),
            ("Lần dùng gần nhất", _format_dt(device.get("last_seen_at", ""))),
            ("Ghi chú", device.get("note", "") or "—"),
        ]

        if device.get("revoked_at"):
            info.insert(6, ("Thu hồi lúc", _format_dt(device.get("revoked_at", ""))))

        for label, value in info:
            row = tk.Frame(self.detail_info_frame, bg=C_CARD)
            row.pack(fill="x", pady=2)

            tk.Label(row, text=f"{label}:", font=FONT_SMALL,
                    fg=C_TEXT_MUTED, bg=C_CARD, width=18, anchor="w").pack(side="left")

            fg = STATUS_COLORS.get(status, C_TEXT_BODY) if label == "Trạng thái" else C_TEXT_BODY
            tk.Label(row, text=value, font=FONT_SMALL,
                    fg=fg, bg=C_CARD, anchor="w", wraplength=200).pack(side="left")

        # Update button states
        self._update_action_buttons(status)

    def _update_action_buttons(self, status: str):
        # Enable/disable buttons based on current status
        self.btn_approve.configure(
            state="normal" if status == STATUS_CHO_DUYET else "disabled")
        self.btn_suspend.configure(
            state="normal" if status in (STATUS_DANG_HOAT_DONG, STATUS_CHO_DUYET) else "disabled")
        self.btn_revoke.configure(
            state="normal" if status != STATUS_DA_THU_HOI else "disabled")
        self.btn_reactivate.configure(
            state="normal" if status in (STATUS_DA_THU_HOI, STATUS_TAM_NGUNG) else "disabled")

    def _change_status(self, new_status: str):
        if not self.selected_device:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một thiết bị.", parent=self)
            return

        device = self.selected_device
        user_name = device.get("user_name", "N/A")
        machine = device.get("machine_name", "N/A")
        status_label = STATUS_LABELS.get(new_status, new_status)

        # Xác nhận rõ ràng
        if new_status == STATUS_DA_THU_HOI:
            confirm_msg = (
                f"⚠️ THU HỒI QUYỀN SỬ DỤNG\n\n"
                f"Thiết bị: {user_name} ({machine})\n\n"
                f"Sau khi thu hồi, ứng dụng trên thiết bị này sẽ hiện thông báo:\n"
                f"\"Quyền sử dụng ứng dụng này không còn hiệu lực.\"\n\n"
                f"Bạn có chắc chắn muốn thu hồi quyền?"
            )
        elif new_status == STATUS_TAM_NGUNG:
            confirm_msg = (
                f"⏸ TẠM NGƯNG QUYỀN SỬ DỤNG\n\n"
                f"Thiết bị: {user_name} ({machine})\n\n"
                f"Thiết bị sẽ tạm thời không thể sử dụng ứng dụng.\n\n"
                f"Bạn có chắc chắn muốn tạm ngưng?"
            )
        elif new_status == STATUS_DANG_HOAT_DONG:
            action = "duyệt" if device.get("status") == STATUS_CHO_DUYET else "kích hoạt lại"
            confirm_msg = (
                f"✅ {action.upper()} THIẾT BỊ\n\n"
                f"Thiết bị: {user_name} ({machine})\n\n"
                f"Bạn có chắc chắn muốn {action} thiết bị này?"
            )
        else:
            confirm_msg = f"Thay đổi trạng thái thành {status_label}?"

        if not messagebox.askyesno("Xác nhận", confirm_msg, parent=self):
            return

        device_uuid = device.get("device_uuid", "")
        success, msg = self.api.update_device_status(device_uuid, new_status)

        if success:
            messagebox.showinfo(
                "Thành công",
                f"Đã cập nhật trạng thái thiết bị thành: {status_label}",
                parent=self,
            )
            self._load_devices()
            self.selected_device["status"] = new_status
            self._update_detail(self.selected_device)
            self._load_device_events(device_uuid)
        else:
            messagebox.showerror("Lỗi", f"Không thể cập nhật:\n{msg}", parent=self)

    def _load_device_events(self, device_uuid: str):
        def _do():
            events = self.api.get_events(device_uuid, 30)
            self.after(0, lambda: self._display_events(events))

        threading.Thread(target=_do, daemon=True).start()

    def _load_all_events(self):
        def _do():
            events = self.api.get_events("", 100)
            self.after(0, lambda: self._display_events(events))

        threading.Thread(target=_do, daemon=True).start()

    def _display_events(self, events: list):
        self.events_text.configure(state="normal")
        self.events_text.delete("1.0", "end")

        if not events:
            self.events_text.insert("end", "Chưa có lịch sử thao tác.\n")
        else:
            for ev in events:
                dt = _format_dt(ev.get("created_at", ""))
                etype = ev.get("event_type", "")
                detail = ev.get("detail", "")
                admin = ev.get("admin_email", "")

                line = f"[{dt}] {etype}"
                if admin:
                    line += f" (bởi {admin})"
                line += f"\n  {detail}\n\n"
                self.events_text.insert("end", line)

        self.events_text.configure(state="disabled")


def _format_dt(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_str[:16] if len(iso_str) > 16 else iso_str


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quản trị quyền sử dụng — Tuyên Bùi")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(bg=C_BG)

        # Căn giữa
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"1100x700+{max(0, (sw - 1100) // 2)}+{max(0, (sh - 700) // 2 - 30)}")
        except Exception:
            pass

        self.current_frame = None
        self._show_login()

    def _show_login(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = LoginFrame(self, on_login_success=self._on_login_success)
        self.current_frame.pack(fill="both", expand=True)

    def _on_login_success(self, auth: SupabaseAuth):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = DashboardFrame(
            self, auth=auth, on_logout=self._show_login
        )
        self.current_frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
