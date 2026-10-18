from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Đảm bảo import an toàn dù chạy từ thư mục nào
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from engine import run_pipeline, save_class_template, RunResult
except ImportError:
    from app.engine import run_pipeline, save_class_template, RunResult


def discover_project_root() -> Path:
    """Xác định thư mục gốc dự án kể cả khi chạy từ outputs/."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    app_root = Path(__file__).resolve().parents[1]
    candidates = [app_root, *list(app_root.parents)[:4]]
    for candidate in candidates:
        if (candidate / "work" / "month_09").is_dir():
            return candidate
        if (candidate / "sources_original").is_dir():
            return candidate
    return app_root


ROOT = discover_project_root()


def default_source_folder() -> Path:
    return ROOT


# ==============================================================================
# DESIGN SYSTEM — Minimalism & Swiss Style (Education Professional)
# Primary: #1E3A5F (Navy), Secondary: #2563EB (Blue), Accent: #059669 (Green)
# Background: #F8FAFC, Card: #FFFFFF, Muted: #F1F3F5
# ==============================================================================

# --- Palette ---
C_BG          = "#F0F4F8"   # Tổng thể: Blue-gray nhạt, sạch
C_BG_STRIPE   = "#E8EEF4"   # Sọc nhẹ giữa các bước
C_CARD        = "#FFFFFF"   # Card thuần trắng
C_CARD_ALT    = "#F8FAFC"   # Card phụ / nền ô input
C_BORDER      = "#D1D9E6"   # Viền: Blue-gray 200
C_BORDER_FOCUS= "#2563EB"   # Viền khi focus

# --- Text ---
C_TEXT        = "#0F172A"   # Chữ chính: Slate 900
C_TEXT_BODY   = "#334155"   # Chữ nội dung: Slate 700
C_TEXT_MUTED  = "#64748B"   # Chữ phụ: Slate 500
C_TEXT_LIGHT  = "#94A3B8"   # Chữ rất nhạt

# --- Bước (Step colors) ---
C_STEP1       = "#2563EB"   # Bước 1: Blue
C_STEP1_BG    = "#EFF6FF"   # Nền bước 1 nhạt
C_STEP2       = "#0F766E"   # Bước 2: Teal
C_STEP2_BG    = "#F0FDFA"   # Nền bước 2 nhạt
C_STEP3       = "#7C3AED"   # Bước 3: Violet (Tổng hợp)
C_STEP3_BG    = "#F5F3FF"   # Nền bước 3 nhạt

# --- Action colors ---
C_PRIMARY     = "#1E3A5F"   # Navy chính (header)
C_BLUE        = "#2563EB"   # Blue hành động
C_BLUE_HOVER  = "#1D4ED8"
C_TEAL        = "#0F766E"   # Teal thiết lập
C_TEAL_HOVER  = "#115E59"
C_RUN         = "#7C3AED"   # Violet nổi bật = nút TỔNG HỢP
C_RUN_HOVER   = "#6D28D9"
C_RUN_ACTIVE  = "#5B21B6"
C_SUCCESS     = "#059669"   # Green thành công
C_SUCCESS_HOVER = "#047857"
C_DANGER      = "#DC2626"   # Red lỗi
C_WARN_BG     = "#FFFBEB"
C_WARN_BORDER = "#FDE68A"
C_WARN_TEXT   = "#92400E"
C_GOLD        = "#92400E"   # Amber bản quyền
C_GOLD_BG     = "#FFFBEB"
C_GOLD_BORDER = "#FCD34D"

# --- State colors ---
STATE_READY    = "#2563EB"
STATE_RUNNING  = "#7C3AED"
STATE_SUCCESS  = "#059669"
STATE_ERROR    = "#DC2626"

# --- Typography ---
_WIN = sys.platform.startswith("win")
FONT_HEAD    = ("Segoe UI", 16, "bold") if _WIN else ("Helvetica", 16, "bold")
FONT_TITLE   = ("Segoe UI", 13, "bold") if _WIN else ("Helvetica", 13, "bold")
FONT_STEP    = ("Segoe UI", 11, "bold") if _WIN else ("Helvetica", 11, "bold")
FONT_BODY    = ("Segoe UI", 10)         if _WIN else ("Helvetica", 10)
FONT_BODY_B  = ("Segoe UI", 10, "bold") if _WIN else ("Helvetica", 10, "bold")
FONT_SMALL   = ("Segoe UI", 9)          if _WIN else ("Helvetica", 9)
FONT_SMALL_I = ("Segoe UI", 9, "italic") if _WIN else ("Helvetica", 9, "italic")
FONT_TINY    = ("Segoe UI", 8)          if _WIN else ("Helvetica", 8)
FONT_MONO    = ("Consolas", 9)          if _WIN else ("Courier", 9)
FONT_BADGE   = ("Segoe UI", 10, "bold") if _WIN else ("Helvetica", 10, "bold")
FONT_NUMBER  = ("Segoe UI", 18, "bold") if _WIN else ("Helvetica", 18, "bold")
FONT_RUN     = ("Segoe UI", 13, "bold") if _WIN else ("Helvetica", 13, "bold")

# --- Spacing & Geometry ---
PAD_OUTER = 20   # Margin xung quanh main box
PAD_CARD  = 20   # Padding bên trong card
GAP_CARD  = 12   # Khoảng cách giữa các card
RADIUS    = 0    # tkinter không hỗ trợ border-radius trực tiếp


def _sep(parent, color=C_BORDER, pady=(0, 0)):
    """Đường kẻ phân cách ngang mỏng."""
    f = tk.Frame(parent, bg=color, height=1)
    f.pack(fill="x", pady=pady)
    return f


def _step_badge(parent, num: str, color: str, bg: str) -> tk.Frame:
    """Badge số bước tròn."""
    badge = tk.Frame(parent, bg=color, width=28, height=28)
    badge.pack_propagate(False)
    tk.Label(badge, text=num, font=("Segoe UI", 10, "bold") if _WIN else ("Helvetica", 10, "bold"),
             fg="#FFFFFF", bg=color).pack(expand=True)
    return badge


class ModernButton(tk.Button):
    """Nút bấm phẳng hiện đại với hiệu ứng hover."""

    def __init__(self, master=None, bg_color=C_BLUE, hover_color=C_BLUE_HOVER,
                 text_color="#FFFFFF", font_spec=None, **kwargs):
        if font_spec is None:
            font_spec = FONT_BODY_B
        self.default_bg = bg_color
        self.hover_bg = hover_color
        self.default_fg = text_color

        padx = kwargs.pop("padx", 18)
        pady = kwargs.pop("pady", 9)

        super().__init__(
            master,
            bg=self.default_bg,
            fg=self.default_fg,
            activebackground=self.hover_bg,
            activeforeground=self.default_fg,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=font_spec,
            padx=padx,
            pady=pady,
            **kwargs
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self.hover_bg)

    def _on_leave(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self.default_bg)

    def set_color(self, bg_color, hover_color):
        self.default_bg = bg_color
        self.hover_bg = hover_color
        if str(self["state"]) != "disabled":
            self.configure(bg=bg_color)


class SecondaryButton(tk.Button):
    """Nút phụ kiểu outline/ghost."""

    def __init__(self, master=None, **kwargs):
        font_spec = kwargs.pop("font_spec", FONT_SMALL)
        padx = kwargs.pop("padx", 14)
        pady = kwargs.pop("pady", 7)
        super().__init__(
            master,
            bg=C_CARD_ALT,
            fg=C_TEXT_BODY,
            activebackground=C_BORDER,
            activeforeground=C_TEXT,
            relief="flat",
            bd=1,
            highlightbackground=C_BORDER,
            highlightthickness=1,
            cursor="hand2",
            font=font_spec,
            padx=padx,
            pady=pady,
            **kwargs
        )
        self.bind("<Enter>", lambda _: self.configure(bg=C_BORDER))
        self.bind("<Leave>", lambda _: self.configure(bg=C_CARD_ALT))


class StyledEntry(tk.Entry):
    """Entry đẹp với viền và nền nhất quán."""

    def __init__(self, master=None, **kwargs):
        super().__init__(
            master,
            font=FONT_BODY,
            bg=C_CARD_ALT,
            fg=C_TEXT,
            insertbackground=C_BLUE,
            relief="solid",
            bd=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_BORDER_FOCUS,
            highlightthickness=1,
            **kwargs
        )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tổng hợp Hạnh kiểm / Rèn luyện — Tuyên Bùi")
        self.geometry("960x780")
        self.minsize(880, 700)
        self.configure(bg=C_BG)

        # Căn giữa cửa sổ trên màn hình
        self._center_window(960, 780)

        # Biến trạng thái
        self.source_var = tk.StringVar(value=str(default_source_folder()))
        self.output_var = tk.StringVar(value=str(ROOT / "outputs"))
        self.status_var = tk.StringVar(value="Sẵn sàng thực hiện")
        self.is_running = False
        self.latest_result: RunResult | None = None
        self._app_state = "ready"  # ready | running | success | error

        # ttk style
        self._setup_styles()

        # Xây dựng giao diện
        self._build_ui()

        # Nhật ký ban đầu
        self._log("✓ Hệ thống sẵn sàng. Dữ liệu xử lý 100% an toàn offline trên máy này.")

    def _center_window(self, width: int, height: int):
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{width}x{height}+{max(0,(sw-width)//2)}+{max(0,(sh-height)//2-20)}")
        except Exception:
            pass

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Progressbar mỏng, màu Violet (TỔNG HỢP)
        style.configure(
            "Run.Horizontal.TProgressbar",
            troughcolor="#E0E7FF",
            background=C_RUN,
            bordercolor="#E0E7FF",
            lightcolor=C_RUN,
            darkcolor=C_RUN,
            thickness=6,
        )
        # Scrollbar nhỏ gọn
        style.configure("Thin.Vertical.TScrollbar", arrowsize=10)

    # ==========================================================================
    # BUILD UI
    # ==========================================================================
    def _build_ui(self):
        # Wrapper toàn màn hình
        root_frame = tk.Frame(self, bg=C_BG)
        root_frame.pack(fill="both", expand=True)

        # --- Top bar cố định (không cuộn) ---
        self._build_topbar(root_frame)

        # --- Vùng nội dung cuộn ---
        content_wrap = tk.Frame(root_frame, bg=C_BG)
        content_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(content_wrap, bg=C_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(content_wrap, orient="vertical", command=canvas.yview,
                                   style="Thin.Vertical.TScrollbar")
        self.scroll_frame = tk.Frame(canvas, bg=C_BG)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_win = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_win, width=event.width)

        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_wheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Padding tổng thể
        main = tk.Frame(self.scroll_frame, bg=C_BG, padx=PAD_OUTER, pady=16)
        main.pack(fill="both", expand=True)

        # --- Thanh tiến trình bước (step indicator) ---
        self._build_step_indicator(main)

        # --- Bước 1: Chọn dữ liệu ---
        self._build_step1(main)

        # --- Bước 2: Thiết lập mẫu lớp ---
        self._build_step2(main)

        # --- Bước 3: Tổng hợp ---
        self._build_step3(main)

        # --- Vùng kết quả (ẩn ban đầu) ---
        self.result_container = tk.Frame(main, bg=C_BG)
        self.result_container.pack(fill="x")
        self._build_result_panel(self.result_container)

        # --- Nhật ký ---
        self._build_log_section(main)

    # --------------------------------------------------------------------------
    # TOP BAR
    # --------------------------------------------------------------------------
    def _build_topbar(self, parent):
        """Thanh tiêu đề cố định ở đầu, không cuộn."""
        bar = tk.Frame(parent, bg=C_PRIMARY, padx=PAD_CARD, pady=0)
        bar.pack(fill="x")

        inner = tk.Frame(bar, bg=C_PRIMARY)
        inner.pack(fill="x", pady=14)

        # Bên trái: icon + tên app
        left = tk.Frame(inner, bg=C_PRIMARY)
        left.pack(side="left", fill="x", expand=True)

        # Icon giáo dục đơn giản bằng canvas
        icon_canvas = tk.Canvas(left, width=36, height=36, bg=C_PRIMARY,
                                highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 12))
        # Vẽ icon sách đơn giản
        icon_canvas.create_rectangle(6, 8, 30, 30, fill="#FFFFFF", outline="", width=0)
        icon_canvas.create_rectangle(6, 8, 17, 30, fill="#E0E7FF", outline="", width=0)
        icon_canvas.create_line(6, 8, 6, 30, fill=C_BLUE, width=3)
        icon_canvas.create_line(10, 13, 26, 13, fill=C_BORDER, width=1)
        icon_canvas.create_line(10, 17, 26, 17, fill=C_BORDER, width=1)
        icon_canvas.create_line(10, 21, 20, 21, fill=C_BORDER, width=1)

        text_block = tk.Frame(left, bg=C_PRIMARY)
        text_block.pack(side="left")

        tk.Label(
            text_block,
            text="Hệ thống Tổng hợp Hạnh kiểm / Rèn luyện",
            font=FONT_HEAD,
            fg="#FFFFFF",
            bg=C_PRIMARY
        ).pack(anchor="w")

        tk.Label(
            text_block,
            text="Giải pháp tự động đánh giá nền nếp học sinh theo tháng · Dành cho Giáo viên Chủ nhiệm",
            font=FONT_SMALL,
            fg="#93C5FD",
            bg=C_PRIMARY
        ).pack(anchor="w", pady=(2, 0))

        # Bên phải: bản quyền + badge offline
        right = tk.Frame(inner, bg=C_PRIMARY)
        right.pack(side="right", anchor="ne")

        # Badge bản quyền
        copy_frame = tk.Frame(right, bg=C_GOLD_BG, bd=1, relief="solid",
                              highlightbackground=C_GOLD_BORDER, highlightthickness=1)
        copy_frame.pack(anchor="ne")
        tk.Label(
            copy_frame,
            text="✦  Bản quyền © Tuyên Bùi  ✦",
            font=FONT_BADGE,
            fg=C_GOLD,
            bg=C_GOLD_BG,
            padx=12,
            pady=5
        ).pack()

        # Badge offline nhỏ bên dưới bản quyền
        offline_frame = tk.Frame(right, bg="#064E3B", bd=0)
        offline_frame.pack(anchor="ne", pady=(5, 0))
        tk.Label(
            offline_frame,
            text="🔒  Xử lý cục bộ — Không gửi dữ liệu ra ngoài",
            font=FONT_TINY,
            fg="#6EE7B7",
            bg="#064E3B",
            padx=10,
            pady=4
        ).pack()

        # Badge trạng thái license (nếu có)
        self._license_badge_frame = None
        license_msg = getattr(self, '_license_status_message', None)
        if license_msg:
            level = getattr(self, '_license_status_level', 'info')
            if level == 'warning':
                badge_bg = "#92400E"
                badge_fg = "#FDE68A"
                icon = "⚡"
            else:
                badge_bg = "#1E3A5F"
                badge_fg = "#93C5FD"
                icon = "✓"

            self._license_badge_frame = tk.Frame(right, bg=badge_bg, bd=0)
            self._license_badge_frame.pack(anchor="ne", pady=(3, 0))
            tk.Label(
                self._license_badge_frame,
                text=f"{icon}  {license_msg}",
                font=FONT_TINY,
                fg=badge_fg,
                bg=badge_bg,
                padx=10,
                pady=3,
                wraplength=280,
                justify="left",
            ).pack()

    # --------------------------------------------------------------------------
    # STEP INDICATOR
    # --------------------------------------------------------------------------
    def _build_step_indicator(self, parent):
        """Thanh hiển thị 3 bước tiến trình nằm ngang."""
        bar = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                       highlightbackground=C_BORDER, highlightthickness=1)
        bar.pack(fill="x", pady=(0, GAP_CARD))

        inner = tk.Frame(bar, bg=C_CARD, pady=12)
        inner.pack(fill="x")

        steps = [
            ("1", "Chọn dữ liệu", "File VnEdu hoặc thư mục tháng", C_STEP1, C_STEP1_BG),
            ("2", "Thiết lập lớp", "Làm 1 lần cho mỗi lớp", C_STEP2, C_STEP2_BG),
            ("3", "Tổng hợp", "Xuất kết quả Excel tự động", C_STEP3, C_STEP3_BG),
        ]

        for i, (num, title, sub, color, bg) in enumerate(steps):
            col = tk.Frame(inner, bg=C_CARD)
            col.pack(side="left", fill="both", expand=True)

            step_inner = tk.Frame(col, bg=bg, padx=16, pady=10)
            step_inner.pack(fill="both", expand=True, padx=4)

            row = tk.Frame(step_inner, bg=bg)
            row.pack(anchor="center")

            # Badge tròn
            badge_f = tk.Frame(row, bg=color, width=30, height=30)
            badge_f.pack(side="left", padx=(0, 10))
            badge_f.pack_propagate(False)
            tk.Label(badge_f, text=num, font=FONT_BODY_B,
                     fg="#FFFFFF", bg=color).pack(expand=True)

            text_col = tk.Frame(row, bg=bg)
            text_col.pack(side="left")

            tk.Label(text_col, text=title, font=FONT_STEP,
                     fg=color, bg=bg).pack(anchor="w")
            tk.Label(text_col, text=sub, font=FONT_TINY,
                     fg=C_TEXT_MUTED, bg=bg).pack(anchor="w")

            # Mũi tên phân cách (trừ bước cuối)
            if i < len(steps) - 1:
                tk.Label(inner, text="›", font=("Segoe UI", 18, "bold") if _WIN else ("Helvetica", 18, "bold"),
                         fg=C_BORDER, bg=C_CARD).pack(side="left")

    # --------------------------------------------------------------------------
    # BƯỚC 1 — CHỌN DỮ LIỆU
    # --------------------------------------------------------------------------
    def _build_step1(self, parent):
        card = self._make_card(parent, accent_color=C_STEP1)
        inner = tk.Frame(card, bg=C_CARD, padx=PAD_CARD, pady=PAD_CARD)
        inner.pack(fill="x")

        # Header bước
        self._step_header(inner, "1", "Chọn dữ liệu đầu vào", C_STEP1,
                          hint="File báo cáo VnEdu (.xlsx / .xls) hoặc thư mục chứa dữ liệu tháng")

        _sep(inner, C_BORDER, (8, 14))

        # --- Nguồn dữ liệu ---
        tk.Label(inner, text="Nguồn dữ liệu", font=FONT_BODY_B,
                 fg=C_TEXT, bg=C_CARD).pack(anchor="w", pady=(0, 4))

        src_row = tk.Frame(inner, bg=C_CARD)
        src_row.pack(fill="x", pady=(0, 12))

        src_entry = StyledEntry(src_row, textvariable=self.source_var)
        src_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        ModernButton(
            src_row,
            text="📄  Chọn file VnEdu",
            bg_color=C_BLUE, hover_color=C_BLUE_HOVER,
            font_spec=FONT_SMALL,
            padx=14, pady=7,
            command=self.choose_vnedu_file
        ).pack(side="left", padx=(0, 6))

        SecondaryButton(
            src_row,
            text="📁  Chọn thư mục",
            font_spec=FONT_SMALL,
            padx=14, pady=7,
            command=self.choose_source_dir
        ).pack(side="left")

        # --- Thư mục lưu kết quả ---
        tk.Label(inner, text="Thư mục lưu kết quả", font=FONT_BODY_B,
                 fg=C_TEXT, bg=C_CARD).pack(anchor="w", pady=(2, 4))

        out_row = tk.Frame(inner, bg=C_CARD)
        out_row.pack(fill="x")

        StyledEntry(out_row, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        SecondaryButton(
            out_row,
            text="📂  Chọn nơi lưu",
            font_spec=FONT_SMALL,
            padx=14, pady=7,
            command=self.choose_output_dir
        ).pack(side="left")

    # --------------------------------------------------------------------------
    # BƯỚC 2 — THIẾT LẬP MẪU LỚP
    # --------------------------------------------------------------------------
    def _build_step2(self, parent):
        card = self._make_card(parent, accent_color=C_STEP2)
        inner = tk.Frame(card, bg=C_CARD, padx=PAD_CARD, pady=PAD_CARD)
        inner.pack(fill="x")

        self._step_header(inner, "2", "Thiết lập mẫu lớp", C_STEP2,
                          hint="Làm 1 lần cho mỗi lớp — các tháng sau chỉ cần Bước 1")

        _sep(inner, C_BORDER, (8, 14))

        action_row = tk.Frame(inner, bg=C_CARD)
        action_row.pack(fill="x")

        ModernButton(
            action_row,
            text="📋  THIẾT LẬP MẪU LỚP",
            bg_color=C_TEAL, hover_color=C_TEAL_HOVER,
            font_spec=FONT_BODY_B,
            padx=20, pady=10,
            command=self.save_template
        ).pack(side="left", padx=(0, 16))

        info_col = tk.Frame(action_row, bg=C_CARD)
        info_col.pack(side="left", fill="both", expand=True)

        tk.Label(
            info_col,
            text="Chọn file Excel mẫu hạnh kiểm chuẩn của lớp",
            font=FONT_BODY_B,
            fg=C_TEXT,
            bg=C_CARD
        ).pack(anchor="w")

        tk.Label(
            info_col,
            text="Hệ thống sẽ đọc danh sách học sinh, sĩ số và điểm nền ban đầu từ file này để khóa cứng.",
            font=FONT_SMALL,
            fg=C_TEXT_MUTED,
            bg=C_CARD,
            wraplength=500,
            justify="left"
        ).pack(anchor="w", pady=(2, 0))

    # --------------------------------------------------------------------------
    # BƯỚC 3 — TỔNG HỢP
    # --------------------------------------------------------------------------
    def _build_step3(self, parent):
        card = self._make_card(parent, accent_color=C_STEP3)
        inner = tk.Frame(card, bg=C_CARD, padx=PAD_CARD, pady=PAD_CARD)
        inner.pack(fill="x")

        self._step_header(inner, "3", "Tổng hợp kết quả", C_STEP3,
                          hint="Tự động nhận diện lớp · Đọc VnEdu · Đối chiếu tiêu chí · Chống trùng · Xuất Excel")

        _sep(inner, C_BORDER, (8, 16))

        # Hàng chứa nút TỔNG HỢP + trạng thái
        run_row = tk.Frame(inner, bg=C_CARD)
        run_row.pack(fill="x", pady=(0, 12))

        # NÚT TỔNG HỢP — nổi bật nhất giao diện
        self.btn_run = ModernButton(
            run_row,
            text="  🚀  TỔNG HỢP  ",
            bg_color=C_RUN, hover_color=C_RUN_HOVER,
            text_color="#FFFFFF",
            font_spec=FONT_RUN,
            padx=30, pady=13,
            command=self.start_pipeline_thread
        )
        self.btn_run.pack(side="left", padx=(0, 20))

        # Panel trạng thái bên phải nút
        state_panel = tk.Frame(run_row, bg=C_CARD)
        state_panel.pack(side="left", fill="both", expand=True)

        # Badge trạng thái (màu thay đổi)
        self.state_badge = tk.Frame(state_panel, bg="#EFF6FF",
                                    bd=1, relief="solid",
                                    highlightbackground="#BFDBFE",
                                    highlightthickness=1)
        self.state_badge.pack(fill="x", pady=(0, 4))

        badge_inner = tk.Frame(self.state_badge, bg="#EFF6FF", padx=12, pady=8)
        badge_inner.pack(fill="x")

        self.state_dot = tk.Label(badge_inner, text="●", font=FONT_BODY_B,
                                   fg=STATE_READY, bg="#EFF6FF")
        self.state_dot.pack(side="left", padx=(0, 8))

        self.state_label = tk.Label(badge_inner, textvariable=self.status_var,
                                     font=FONT_BODY_B, fg=STATE_READY,
                                     bg="#EFF6FF", anchor="w",
                                     wraplength=460, justify="left")
        self.state_label.pack(side="left", fill="x", expand=True)

        # Thanh tiến trình indeterminate
        self.progress_bar = ttk.Progressbar(
            inner,
            style="Run.Horizontal.TProgressbar",
            mode="indeterminate"
        )
        self.progress_bar.pack(fill="x", pady=(0, 0))

        # Ghi chú nhỏ bên dưới
        note_row = tk.Frame(inner, bg=C_CARD)
        note_row.pack(fill="x", pady=(10, 0))
        tk.Label(
            note_row,
            text="ℹ️  Hệ thống tự động áp trần điểm cộng, xử lý trùng lặp và tạo danh sách \"Cần GVCN xác nhận\" ngay trong file Excel.",
            font=FONT_TINY,
            fg=C_TEXT_MUTED,
            bg=C_CARD,
            wraplength=860,
            justify="left"
        ).pack(anchor="w")

    # --------------------------------------------------------------------------
    # KẾT QUẢ
    # --------------------------------------------------------------------------
    def _build_result_panel(self, parent):
        """Card kết quả — ẩn ban đầu, hiện khi tổng hợp xong."""
        self.result_card = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                                    highlightbackground="#86EFAC",
                                    highlightthickness=2)
        # Không pack ngay — sẽ pack sau khi hoàn tất

        inner = tk.Frame(self.result_card, bg=C_CARD, padx=PAD_CARD, pady=PAD_CARD)
        inner.pack(fill="x")

        # Tiêu đề thành công
        header_row = tk.Frame(inner, bg=C_CARD)
        header_row.pack(fill="x", pady=(0, 14))

        success_badge = tk.Frame(header_row, bg="#DCFCE7", padx=12, pady=6)
        success_badge.pack(side="left")
        tk.Label(success_badge, text="✅  KẾT QUẢ HOÀN TẤT",
                 font=FONT_TITLE, fg="#166534", bg="#DCFCE7").pack()

        # Lưới 4 ô thống kê
        stats_frame = tk.Frame(inner, bg=C_CARD)
        stats_frame.pack(fill="x", pady=(0, 14))

        self.stat_students     = self._make_stat(stats_frame, "Học sinh", "0",
                                                  "👨‍🎓", "#EFF6FF", "#1D4ED8")
        self.stat_transactions = self._make_stat(stats_frame, "Giao dịch", "0",
                                                  "📋", "#F0FDF4", "#15803D")
        self.stat_reviews      = self._make_stat(stats_frame, "Cần xác nhận", "0",
                                                  "⚠️", "#FFF7ED", "#C2410C")
        self.stat_duplicates   = self._make_stat(stats_frame, "Trùng lặp", "0",
                                                  "🔄", "#F8FAFC", "#475569")

        for box in (self.stat_students, self.stat_transactions,
                    self.stat_reviews, self.stat_duplicates):
            box.pack(side="left", fill="both", expand=True, padx=(0, 8))
        # Remove last padx
        self.stat_duplicates.pack_configure(padx=0)

        _sep(inner, C_BORDER, (0, 12))

        # File kết quả
        file_area = tk.Frame(inner, bg=C_CARD_ALT, bd=1, relief="solid",
                             highlightbackground=C_BORDER, highlightthickness=1,
                             padx=14, pady=12)
        file_area.pack(fill="x", pady=(0, 12))

        self.lbl_result_file = tk.Label(
            file_area,
            text="File kết quả: (chưa có)",
            font=FONT_BODY,
            fg=C_TEXT_BODY,
            bg=C_CARD_ALT,
            anchor="w",
            wraplength=800,
            justify="left"
        )
        self.lbl_result_file.pack(fill="x", pady=(0, 10))

        # Nút mở file / thư mục
        btn_row = tk.Frame(file_area, bg=C_CARD_ALT)
        btn_row.pack(fill="x")

        self.btn_open_file = ModernButton(
            btn_row,
            text="📊  Mở file Excel kết quả",
            bg_color=C_SUCCESS, hover_color=C_SUCCESS_HOVER,
            font_spec=FONT_BODY_B,
            padx=18, pady=9,
            command=self.open_output_file
        )
        self.btn_open_file.pack(side="left", padx=(0, 10))

        self.btn_open_folder = ModernButton(
            btn_row,
            text="📁  Mở thư mục kết quả",
            bg_color=C_BLUE, hover_color=C_BLUE_HOVER,
            font_spec=FONT_BODY,
            padx=18, pady=9,
            command=self.open_output_folder
        )
        self.btn_open_folder.pack(side="left")

    def _make_stat(self, parent, label: str, value: str,
                   icon: str, bg: str, fg: str) -> tk.Frame:
        box = tk.Frame(parent, bg=bg, bd=1, relief="solid",
                       highlightbackground=C_BORDER, highlightthickness=1,
                       padx=10, pady=10)
        tk.Label(box, text=icon, font=("Segoe UI Emoji", 14) if _WIN else FONT_TITLE,
                 bg=bg).pack(anchor="center")
        lbl_val = tk.Label(box, text=value, font=FONT_NUMBER, fg=fg, bg=bg)
        lbl_val.pack(anchor="center", pady=(2, 1))
        tk.Label(box, text=label, font=FONT_SMALL, fg=C_TEXT_MUTED, bg=bg).pack(anchor="center")
        box.val_label = lbl_val
        return box

    # --------------------------------------------------------------------------
    # NHẬT KÝ
    # --------------------------------------------------------------------------
    def _build_log_section(self, parent):
        log_wrap = tk.Frame(parent, bg=C_BG)
        log_wrap.pack(fill="both", expand=True, pady=(8, 0))

        hdr = tk.Frame(log_wrap, bg=C_BG)
        hdr.pack(fill="x", pady=(0, 4))

        tk.Label(hdr, text="Nhật ký hoạt động", font=FONT_SMALL,
                 fg=C_TEXT_MUTED, bg=C_BG).pack(side="left")

        tk.Button(
            hdr,
            text="Xóa nhật ký",
            font=FONT_TINY,
            fg=C_TEXT_LIGHT,
            bg=C_BG,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._clear_log
        ).pack(side="right")

        log_border = tk.Frame(log_wrap, bg=C_CARD, bd=1, relief="solid",
                              highlightbackground=C_BORDER, highlightthickness=1)
        log_border.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_border,
            height=6,
            bg=C_CARD,
            fg=C_TEXT_BODY,
            font=FONT_MONO,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            wrap="word",
            state="normal"
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = ttk.Scrollbar(log_border, orient="vertical",
                                    command=self.log_text.yview,
                                    style="Thin.Vertical.TScrollbar")
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    # --------------------------------------------------------------------------
    # HELPERS: Card & Step header
    # --------------------------------------------------------------------------
    def _make_card(self, parent, accent_color: str = C_BORDER) -> tk.Frame:
        """Tạo card với viền trái màu accent."""
        wrapper = tk.Frame(parent, bg=C_CARD, bd=1, relief="solid",
                           highlightbackground=C_BORDER, highlightthickness=1)
        wrapper.pack(fill="x", pady=(0, GAP_CARD))

        # Thanh màu trái (accent strip)
        strip = tk.Frame(wrapper, bg=accent_color, width=4)
        strip.pack(side="left", fill="y")
        strip.pack_propagate(False)

        # Frame nội dung bên phải thanh màu
        content = tk.Frame(wrapper, bg=C_CARD)
        content.pack(side="left", fill="both", expand=True)
        return content

    def _step_header(self, parent, num: str, title: str,
                     color: str, hint: str = ""):
        row = tk.Frame(parent, bg=C_CARD)
        row.pack(fill="x", pady=(0, 0))

        # Badge số
        badge = tk.Frame(row, bg=color, width=32, height=32)
        badge.pack(side="left", padx=(0, 12))
        badge.pack_propagate(False)
        tk.Label(badge, text=num, font=FONT_BODY_B,
                 fg="#FFFFFF", bg=color).pack(expand=True)

        col = tk.Frame(row, bg=C_CARD)
        col.pack(side="left", fill="both", expand=True)

        tk.Label(col, text=f"Bước {num} — {title}",
                 font=FONT_TITLE, fg=C_TEXT, bg=C_CARD).pack(anchor="w")

        if hint:
            tk.Label(col, text=hint, font=FONT_SMALL_I,
                     fg=C_TEXT_MUTED, bg=C_CARD,
                     wraplength=700, justify="left").pack(anchor="w", pady=(1, 0))

    # --------------------------------------------------------------------------
    # LOG HELPERS
    # --------------------------------------------------------------------------
    def _log(self, message: str):
        t = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{t}]  {message}\n")
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    # --------------------------------------------------------------------------
    # CẬP NHẬT TRẠNG THÁI
    # --------------------------------------------------------------------------
    def _set_state(self, state: str, message: str):
        """Cập nhật badge trạng thái trực quan."""
        self._app_state = state
        self.status_var.set(message)

        colors = {
            "ready":   (STATE_READY,   "#EFF6FF", "#BFDBFE"),
            "running": (STATE_RUNNING, "#F5F3FF", "#DDD6FE"),
            "success": (STATE_SUCCESS, "#F0FDF4", "#86EFAC"),
            "error":   (STATE_ERROR,   "#FEF2F2", "#FECACA"),
        }
        fg, bg, border = colors.get(state, colors["ready"])

        self.state_dot.configure(fg=fg, bg=bg)
        self.state_label.configure(fg=fg, bg=bg)

        # Cập nhật frame badge
        badge_inner = self.state_dot.master
        badge_inner.configure(bg=bg)
        self.state_badge.configure(highlightbackground=border)
        self.state_badge.configure(bg=bg)

        # Labels trạng thái
        labels_text = {
            "ready":   "⬤  Sẵn sàng",
            "running": "⬤  Đang tổng hợp...",
            "success": "⬤  Hoàn tất",
            "error":   "⬤  Có lỗi",
        }
        self.state_dot.configure(text=labels_text.get(state, "⬤"))

    # --------------------------------------------------------------------------
    # HÀM CHỌN FILE & THƯ MỤC (giữ nguyên 100% logic nghiệp vụ)
    # --------------------------------------------------------------------------
    def choose_vnedu_file(self):
        initial = self.source_var.get()
        initial_dir = str(Path(initial).parent) if Path(initial).is_file() else initial
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(ROOT)

        value = filedialog.askopenfilename(
            title="Chọn file báo cáo chi tiết VnEdu (.xlsx hoặc .xls)",
            initialdir=initial_dir,
            filetypes=[
                ("Báo cáo Excel VnEdu", "*.xlsx *.xls"),
                ("Tất cả tệp", "*.*")
            ],
        )
        if value:
            self.source_var.set(value)
            self._log(f"Đã chọn file VnEdu: {Path(value).name}")
            self._set_state("ready", f"Đã chọn: {Path(value).name}")

    def choose_source_dir(self):
        initial = self.source_var.get()
        if not initial or not Path(initial).exists():
            initial = str(ROOT)

        value = filedialog.askdirectory(
            title="Chọn thư mục chứa dữ liệu tháng",
            initialdir=initial
        )
        if value:
            self.source_var.set(value)
            self._log(f"Đã chọn thư mục nguồn: {Path(value).name}")
            self._set_state("ready", f"Đã chọn thư mục: {Path(value).name}")

    def choose_output_dir(self):
        initial = self.output_var.get()
        if not initial or not Path(initial).exists():
            initial = str(ROOT)

        value = filedialog.askdirectory(
            title="Chọn thư mục lưu kết quả tổng hợp",
            initialdir=initial
        )
        if value:
            self.output_var.set(value)
            self._log(f"Đã chọn thư mục lưu: {value}")

    def save_template(self):
        value = filedialog.askopenfilename(
            title="Chọn file Excel mẫu hạnh kiểm của lớp",
            initialdir=str(ROOT),
            filetypes=[("File Excel", "*.xlsx")],
        )
        if not value:
            return

        try:
            self._log(f"Đang thiết lập mẫu lớp từ file: {Path(value).name}...")
            destination, profile, students = save_class_template(value, ROOT)
            self._log(f"Thiết lập thành công mẫu lớp {profile.class_name} ({len(students)} học sinh).")
            messagebox.showinfo(
                "Đã thiết lập mẫu lớp thành công",
                f"Đã lưu bản sao mẫu lớp: {profile.class_name}\n"
                f"Sĩ số nhận diện: {len(students)} học sinh.\n\n"
                f"Từ các tháng tiếp theo, Thầy/Cô chỉ cần chọn file VnEdu của lớp này ở Bước 1.\n\n"
                f"Vị trí lưu: {destination}",
            )
        except Exception as exc:
            self._log(f"Lỗi thiết lập mẫu lớp: {exc}")
            messagebox.showerror(
                "Không thể thiết lập mẫu lớp",
                f"Hệ thống không thể đọc file mẫu này:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra file Excel có đúng định dạng mẫu đánh giá hạnh kiểm của lớp hay không."
            )

    # --------------------------------------------------------------------------
    # LUỒNG TỔNG HỢP CHẠY NỀN (BACKGROUND THREADING)
    # --------------------------------------------------------------------------
    def start_pipeline_thread(self):
        if self.is_running:
            return

        source = self.source_var.get().strip()
        output = self.output_var.get().strip()

        if not source:
            messagebox.showwarning(
                "Chưa chọn dữ liệu",
                "Thầy/Cô chưa chọn file hoặc thư mục dữ liệu nguồn.\n\n"
                "👉 Hướng dẫn: Vui lòng bấm 'Chọn file VnEdu' hoặc 'Chọn thư mục' ở Bước 1."
            )
            return

        if not Path(source).exists():
            messagebox.showerror(
                "Đường dẫn không tồn tại",
                f"Không tìm thấy file hoặc thư mục nguồn tại:\n{source}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra lại đường dẫn đã chọn hoặc di chuyển file về đúng vị trí."
            )
            return

        if not output:
            output = str(ROOT / "outputs")
            self.output_var.set(output)

        # Kiểm tra license trước khi cho phép Tổng hợp dữ liệu
        try:
            from app.license_client import check_license
            lic_res = check_license()
            if not lic_res.allowed:
                messagebox.showerror(
                    "Quyền sử dụng không hợp lệ",
                    lic_res.message or "Thiết bị của Thầy/Cô chưa được cấp quyền sử dụng chức năng này.\nVui lòng liên hệ tác giả để được hỗ trợ."
                )
                try:
                    self.destroy()
                except Exception:
                    pass
                import os
                os._exit(0)
                return
        except Exception:
            pass

        # Khóa nút + kích hoạt tiến trình
        self.is_running = True
        self.btn_run.configure(state="disabled", text="  ⏳  ĐANG XỬ LÝ...  ")
        self.btn_run.set_color("#6D28D9", "#6D28D9")
        self.progress_bar.start(10)
        self._set_state("running", "Đang tổng hợp dữ liệu... Vui lòng đợi trong giây lát.")
        self.config(cursor="wait")

        # Ẩn kết quả cũ
        try:
            self.result_card.pack_forget()
        except Exception:
            pass

        self._log(f"Bắt đầu tổng hợp từ: {Path(source).name}")

        # Tiểu trình nền — cửa sổ không bị 'Not Responding'
        thread = threading.Thread(
            target=self._worker_run,
            args=(source, output),
            daemon=True
        )
        thread.start()

    def _worker_run(self, source: str, output: str):
        try:
            start_time = time.time()
            result = run_pipeline(source, output)
            elapsed = time.time() - start_time
            self.after(0, self._on_success, result, elapsed)
        except Exception as exc:
            tb_str = traceback.format_exc()
            self.after(0, self._on_error, exc, tb_str)

    def _on_success(self, result: RunResult, elapsed: float):
        self.is_running = False
        self.progress_bar.stop()
        self.btn_run.configure(state="normal", text="  🚀  TỔNG HỢP  ")
        self.btn_run.set_color(C_RUN, C_RUN_HOVER)
        self.config(cursor="")
        self.latest_result = result

        # Cập nhật số liệu thống kê
        self.stat_students.val_label.configure(text=str(result.student_count))
        self.stat_transactions.val_label.configure(text=str(result.transaction_count))
        self.stat_reviews.val_label.configure(text=str(result.review_count))
        self.stat_duplicates.val_label.configure(text=str(result.duplicate_count))

        out_name = Path(result.output_file).name
        self.lbl_result_file.configure(
            text=f"📄  {out_name}\n📁  {result.output_file}"
        )

        # Hiển thị card kết quả
        self.result_card.pack(fill="x", pady=(0, GAP_CARD))

        # Trạng thái
        status_msg = (
            f"Hoàn tất ({elapsed:.1f}s) — "
            f"{result.student_count} học sinh · "
            f"{result.transaction_count} giao dịch · "
            f"{result.review_count} mục cần xác nhận"
        )
        self._set_state("success", status_msg)

        self._log(f"✓ Tổng hợp xong ({elapsed:.1f}s). Xuất ra: {out_name}")
        if result.review_count > 0:
            self._log(f"  ⚠  {result.review_count} mục cần GVCN xác nhận → sheet 'CAN_GVCN_XAC_NHAN'.")

        # Hộp thoại thông báo hoàn tất
        info_text = (
            f"Đã hoàn tất tổng hợp dữ liệu!\n\n"
            f"• Số học sinh: {result.student_count}\n"
            f"• Tổng số giao dịch: {result.transaction_count}\n"
            f"• Giao dịch trùng đã xử lý: {result.duplicate_count}\n"
            f"• Mục cần GVCN xác nhận: {result.review_count}\n\n"
            f"File kết quả:\n{result.output_file}\n\n"
            "Thầy/Cô hãy kiểm tra sheet 'CAN_GVCN_XAC_NHAN' trong file Excel trước khi sử dụng chính thức."
        )
        messagebox.showinfo("Tổng hợp hoàn tất", info_text)

    def _on_error(self, exc: Exception, tb_str: str):
        self.is_running = False
        self.progress_bar.stop()
        self.btn_run.configure(state="normal", text="  🚀  TỔNG HỢP  ")
        self.btn_run.set_color(C_RUN, C_RUN_HOVER)
        self.config(cursor="")

        # Ghi log lỗi ra file hệ thống
        log_file = ROOT / "work" / "loi_he_thong.txt"
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text(tb_str, encoding="utf-8")
            log_note = f"\n\nChi tiết kỹ thuật đã được lưu tại:\n{log_file}"
        except Exception:
            log_note = ""

        err_text = str(exc)
        self._log(f"✗ LỖI: {err_text}")
        self._set_state("error", f"Chưa thể tổng hợp: {err_text}")

        # Phân loại lỗi và hướng dẫn tiếng Việt
        if isinstance(exc, PermissionError) or "Permission denied" in err_text or "[Errno 13]" in err_text:
            messagebox.showerror(
                "File Excel đang mở",
                "File Excel kết quả đang được mở trong Microsoft Excel hoặc một chương trình khác.\n\n"
                "👉 Hướng dẫn xử lý:\n"
                "1. Thầy/Cô vui lòng ĐÓNG file Excel đó lại.\n"
                "2. Sau đó bấm 'TỔNG HỢP' để hệ thống xuất lại file."
                f"{log_note}"
            )
        elif "chưa có mẫu" in err_text.lower() or "không tìm thấy mẫu" in err_text.lower() or "no template" in err_text.lower():
            messagebox.showerror(
                "Chưa có mẫu lớp",
                f"{err_text}\n\n"
                "👉 Hướng dẫn xử lý:\n"
                "1. Bấm nút 'THIẾT LẬP MẪU LỚP' ở Bước 2.\n"
                "2. Chọn file Excel mẫu hạnh kiểm chuẩn của lớp.\n"
                "3. Sau đó bấm 'TỔNG HỢP' lại."
                f"{log_note}"
            )
        else:
            messagebox.showerror(
                "Có lỗi xảy ra",
                f"Hệ thống gặp sự cố trong quá trình xử lý:\n{err_text}\n\n"
                "👉 Hướng dẫn xử lý:\n"
                "- Kiểm tra xem file báo cáo VnEdu có đang mở hoặc bị khóa hay không.\n"
                "- Đảm bảo file đúng định dạng báo cáo nền nếp / hạnh kiểm."
                f"{log_note}"
            )

    # --------------------------------------------------------------------------
    # MỞ FILE / FOLDER (giữ nguyên 100% logic)
    # --------------------------------------------------------------------------
    def open_output_file(self):
        if not self.latest_result or not self.latest_result.output_file:
            messagebox.showinfo("Thông báo", "Chưa có file kết quả để mở.")
            return

        file_path = Path(self.latest_result.output_file)
        if not file_path.exists():
            messagebox.showerror("Không tìm thấy file",
                                  f"File không tồn tại tại:\n{file_path}")
            return

        try:
            os.startfile(str(file_path))
            self._log(f"Đã mở file Excel: {file_path.name}")
        except Exception as exc:
            messagebox.showerror("Không thể mở file", f"Lỗi khi mở file Excel:\n{exc}")

    def open_output_folder(self):
        folder = None
        if self.latest_result and self.latest_result.output_file:
            folder = Path(self.latest_result.output_file).parent
        else:
            folder = Path(self.output_var.get())

        if not folder or not folder.exists():
            folder = ROOT / "outputs"
            folder.mkdir(parents=True, exist_ok=True)

        try:
            os.startfile(str(folder))
            self._log(f"Đã mở thư mục: {folder}")
        except Exception as exc:
            messagebox.showerror("Không thể mở thư mục",
                                  f"Lỗi khi mở thư mục:\n{exc}")


def _run_with_license_check():
    """Khởi chạy ứng dụng với kiểm tra quyền sử dụng."""
    # Tạo root ẩn để kiểm tra license
    root_check = tk.Tk()
    root_check.withdraw()  # Ẩn cửa sổ

    try:
        from app.license_ui import run_license_check_ui
        allowed = run_license_check_ui(root_check)
    except ImportError:
        # Nếu module license chưa có, cho chạy bình thường
        allowed = True
    except Exception:
        # Lỗi không mong đợi — vẫn cho chạy
        allowed = True

    root_check.destroy()

    if not allowed:
        return

    # Khởi chạy ứng dụng chính
    app = App()

    # Chuyển thông tin license status sang App (nếu có)
    license_msg = getattr(root_check, '_license_status_message', None)
    if license_msg:
        app._license_status_message = license_msg
        app._license_status_level = getattr(root_check, '_license_status_level', 'info')

    # Khởi động bộ giám sát bản quyền thời gian thực (Heartbeat định kỳ 20s + FocusIn)
    try:
        from app.license_ui import start_license_monitor
        monitor = start_license_monitor(app)

        def _on_window_close():
            monitor.stop()
            app.destroy()

        app.protocol("WM_DELETE_WINDOW", _on_window_close)
    except Exception:
        pass

    app.mainloop()


if __name__ == "__main__":
    _run_with_license_check()
