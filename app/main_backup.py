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

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from engine import run_pipeline, save_class_template, RunResult
except ImportError:
    from app.engine import run_pipeline, save_class_template, RunResult


def discover_project_root() -> Path:
    """Xac dinh thu muc goc du an."""
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
# DESIGN SYSTEM - Flat Design + Soft UI, Vietnamese-optimized
# Palette: Teal Primary / Orange CTA / Mint background
# Font: Segoe UI (Windows built-in, full Vietnamese support)
# ==============================================================================

C_BG          = "#F0FDFA"
C_BG_ALT      = "#E6FAF8"
C_CARD        = "#FFFFFF"
C_CARD_BORDER = "#99F6E4"
C_CARD_SHADOW = "#D0F5EF"

C_TEXT_H1     = "#134E4A"
C_TEXT_BODY   = "#1E293B"
C_TEXT_MUTED  = "#475569"

C_PRIMARY     = "#0D9488"
C_PRIMARY_HOV = "#0F766E"
C_PRIMARY_ACT = "#115E59"

C_CTA         = "#EA580C"
C_CTA_HOV     = "#C2410C"

C_SUCCESS     = "#16A34A"
C_SUCCESS_HOV = "#15803D"
C_SUCCESS_BG  = "#F0FDF4"
C_SUCCESS_TXT = "#14532D"

C_ERROR_BG    = "#FEF2F2"
C_ERROR_TXT   = "#7F1D1D"

C_RUNNING_BG  = "#EFF6FF"
C_RUNNING_TXT = "#1E40AF"

C_STAT_B_BG   = "#EFF6FF"
C_STAT_B_TXT  = "#1D4ED8"
C_STAT_G_BG   = "#F0FDF4"
C_STAT_G_TXT  = "#15803D"
C_STAT_O_BG   = "#FFF7ED"
C_STAT_O_TXT  = "#C2410C"
C_STAT_S_BG   = "#F8FAFC"
C_STAT_S_TXT  = "#475569"

C_GOLD_TXT    = "#92400E"
C_GOLD_BG     = "#FEF3C7"

C_INPUT_BG    = "#F8FAFC"
C_INPUT_BRD   = "#CBD5E1"

C_STEP2_BG    = "#0F766E"
C_STEP3_BG    = "#EA580C"

C_PROG_BG     = "#D0F5EF"
C_PROG_FG     = "#0D9488"
C_PROG_RUN    = "#EA580C"

FONT = "Segoe UI" if sys.platform.startswith("win") else "Helvetica Neue"


class FlatButton(tk.Button):
    def __init__(self, master=None, *, bg_color, hover_color,
                 text_color="#FFFFFF", font_spec=None, px=18, py=9, **kwargs):
        self._bg = bg_color
        self._hov = hover_color
        if font_spec is None:
            font_spec = (FONT, 10, "bold")
        super().__init__(
            master, bg=bg_color, fg=text_color,
            activebackground=hover_color, activeforeground=text_color,
            relief="flat", bd=0, cursor="hand2",
            font=font_spec, padx=px, pady=py, **kwargs,
        )
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _enter(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._hov)

    def _leave(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._bg)

    def set_colors(self, bg, hov):
        self._bg = bg
        self._hov = hov
        if str(self["state"]) != "disabled":
            self.configure(bg=bg)


class StatusBadge(tk.Label):
    STATES = {
        "ready":   ("#E0FDF4", "#065F46", "\u25cf San sang thuc hien"),
        "running": (C_RUNNING_BG, C_RUNNING_TXT, "\u21bb Dang xu ly..."),
        "success": (C_SUCCESS_BG, C_SUCCESS_TXT, "\u2713 Hoan tat"),
        "error":   (C_ERROR_BG, C_ERROR_TXT, "\u2715 Co loi"),
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, relief="flat", padx=14, pady=5,
                         font=(FONT, 9, "bold"), **kwargs)
        self.set_state("ready")

    def set_state(self, state, msg=""):
        bg, fg, default_msg = self.STATES.get(state, self.STATES["ready"])
        self.configure(bg=bg, fg=fg, text=msg or default_msg)


class SectionCard(tk.Frame):
    def __init__(self, master, accent_color=None, **kwargs):
        if accent_color is None:
            accent_color = C_PRIMARY
        super().__init__(master, bg=C_CARD, **kwargs)
        tk.Frame(self, bg=accent_color, width=5).pack(side="left", fill="y")
        self._inner = tk.Frame(self, bg=C_CARD)
        self._inner.pack(side="left", fill="both", expand=True)

    @property
    def inner(self):
        return self._inner


class StepHeader(tk.Frame):
    def __init__(self, master, step_num, title, hint="", num_bg=None, **kwargs):
        if num_bg is None:
            num_bg = C_PRIMARY
        super().__init__(master, bg=C_CARD, **kwargs)
        tk.Label(self, text=step_num, width=2,
                 font=(FONT, 10, "bold"), fg="#FFFFFF", bg=num_bg,
                 padx=6, pady=4).pack(side="left")
        tk.Label(self, text=title,
                 font=(FONT, 12, "bold"), fg=C_TEXT_H1, bg=C_CARD
                 ).pack(side="left", padx=(10, 0))
        if hint:
            tk.Label(self, text=hint,
                     font=(FONT, 9, "italic"), fg=C_TEXT_MUTED, bg=C_CARD
                     ).pack(side="left", padx=(8, 0), pady=(3, 0))


class FieldRow(tk.Frame):
    def __init__(self, master, label, textvariable, **kwargs):
        super().__init__(master, bg=C_CARD, **kwargs)
        tk.Label(self, text=label, font=(FONT, 9, "bold"),
                 fg=C_TEXT_MUTED, bg=C_CARD, width=20, anchor="w"
                 ).pack(side="left")
        self.entry = tk.Entry(
            self, textvariable=textvariable,
            font=(FONT, 10), bg=C_INPUT_BG, fg=C_TEXT_BODY,
            relief="solid", bd=1,
            highlightthickness=2,
            highlightbackground=C_INPUT_BRD,
            highlightcolor=C_PRIMARY,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

    def add_button(self, text, command, bg=None, hov=None,
                   fg="#FFFFFF", font_spec=None, px=12, py=6):
        if bg is None:
            bg = C_PRIMARY
        if hov is None:
            hov = C_PRIMARY_HOV
        if font_spec is None:
            font_spec = (FONT, 9, "bold")
        btn = FlatButton(self, text=text, command=command,
                         bg_color=bg, hover_color=hov,
                         text_color=fg, font_spec=font_spec, px=px, py=py)
        btn.pack(side="left", padx=(0, 5))
        return btn


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("He thong Tong hop Hanh kiem / Ren luyen")
        self.geometry("960x760")
        self.minsize(880, 680)
        self.configure(bg=C_BG)
        self._center_window(960, 760)

        self.source_var = tk.StringVar(value=str(default_source_folder()))
        self.output_var = tk.StringVar(value=str(ROOT / "outputs"))
        self.is_running = False
        self.latest_result = None

        self._setup_ttk_styles()
        self._build_ui()
        self._log("He thong khoi dong thanh cong. Du lieu xu ly an toan 100% tren may tinh nay.")

    def _center_window(self, w, h):
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2-20)}")
        except Exception:
            pass

    def _setup_ttk_styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Teal.Horizontal.TProgressbar",
                    troughcolor=C_PROG_BG, background=C_PROG_FG,
                    bordercolor=C_PROG_BG, lightcolor=C_PROG_FG,
                    darkcolor=C_PROG_FG, thickness=8)
        s.configure("Orange.Horizontal.TProgressbar",
                    troughcolor="#FED7AA", background=C_PROG_RUN,
                    bordercolor="#FED7AA", lightcolor=C_PROG_RUN,
                    darkcolor=C_PROG_RUN, thickness=8)

    def _build_ui(self):
        outer = tk.Frame(self, bg=C_BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=C_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self._frame = tk.Frame(canvas, bg=C_BG)
        self._frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        cw = canvas.create_window((0, 0), window=self._frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=vsb.set)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        content = tk.Frame(self._frame, bg=C_BG, padx=24, pady=20)
        content.pack(fill="both", expand=True)
        self._build_header(content)
        self._build_step1(content)
        self._build_step2(content)
        self._build_step3(content)
        self._result_host = tk.Frame(content, bg=C_BG)
        self._result_host.pack(fill="x")
        self._build_result_dashboard(self._result_host)
        self._build_log(content)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=C_CARD)
        hdr.pack(fill="x", pady=(0, 16))
        tk.Frame(hdr, bg=C_PRIMARY, height=4).pack(fill="x", side="top")
        inner = tk.Frame(hdr, bg=C_CARD, padx=24, pady=18)
        inner.pack(fill="x")
        left = tk.Frame(inner, bg=C_CARD)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left,
                 text="He thong Tong hop Hanh kiem / Ren luyen",
                 font=(FONT, 18, "bold"), fg=C_TEXT_H1, bg=C_CARD
                 ).pack(anchor="w")
        tk.Label(left,
                 text="Giai phap tu dong hoa danh gia hanh kiem hoc sinh theo thang - danh cho GVCN",
                 font=(FONT, 10), fg=C_TEXT_MUTED, bg=C_CARD
                 ).pack(anchor="w", pady=(3, 0))
        notice_row = tk.Frame(left, bg=C_CARD)
        notice_row.pack(anchor="w", pady=(8, 0))
        tk.Label(notice_row, text="  OFFLINE  ",
                 font=(FONT, 8, "bold"), fg="#FFFFFF", bg=C_PRIMARY,
                 padx=6, pady=3).pack(side="left")
        tk.Label(notice_row,
                 text="  Du lieu hoc sinh chi xu ly cuc bo tren may nay - khong gui di bat ky dau.",
                 font=(FONT, 9), fg="#047857", bg=C_CARD
                 ).pack(side="left")
        right = tk.Frame(inner, bg=C_CARD)
        right.pack(side="right", anchor="ne", padx=(12, 0))
        tk.Label(right,
                 text="  \u2726  Ban quyen \u00a9 Tuyen Bui  \u2726  ",
                 font=(FONT, 9, "bold"), fg=C_GOLD_TXT, bg=C_GOLD_BG,
                 relief="solid", bd=1, padx=10, pady=6
                 ).pack(anchor="ne")
        tk.Frame(hdr, bg=C_CARD_BORDER, height=1).pack(fill="x", side="bottom")

    def _make_card(self, parent, accent=None):
        if accent is None:
            accent = C_PRIMARY
        wrap = tk.Frame(parent, bg=C_CARD_SHADOW)
        wrap.pack(fill="x", pady=(0, 14))
        card = SectionCard(wrap, accent_color=accent,
                           highlightbackground=C_CARD_BORDER,
                           highlightthickness=1)
        card.pack(fill="x", pady=(0, 2))
        return card

    def _build_step1(self, parent):
        card = self._make_card(parent, accent=C_PRIMARY)
        inner = card.inner
        pad = tk.Frame(inner, bg=C_CARD, padx=20, pady=16)
        pad.pack(fill="x")
        StepHeader(pad, "1", "Chon du lieu",
                   "(File bao cao VnEdu hoac thu muc chua du lieu thang)",
                   num_bg=C_PRIMARY).pack(anchor="w", pady=(0, 14))
        src_row = FieldRow(pad, "Nguon du lieu:", self.source_var)
        src_row.pack(fill="x", pady=(0, 8))
        src_row.add_button("Chon file VnEdu...", self.choose_vnedu_file,
                           bg=C_PRIMARY, hov=C_PRIMARY_HOV, px=14, py=7)
        src_row.add_button("Chon thu muc...", self.choose_source_dir,
                           bg=C_CARD, hov="#E2E8F0", fg=C_TEXT_BODY,
                           font_spec=(FONT, 9), px=12, py=7)
        out_row = FieldRow(pad, "Luu ket qua vao:", self.output_var)
        out_row.pack(fill="x")
        out_row.add_button("Chon noi luu...", self.choose_output_dir,
                           bg=C_CARD, hov="#E2E8F0", fg=C_TEXT_BODY,
                           font_spec=(FONT, 9), px=12, py=7)

    def _build_step2(self, parent):
        card = self._make_card(parent, accent=C_STEP2_BG)
        inner = card.inner
        pad = tk.Frame(inner, bg=C_CARD, padx=20, pady=16)
        pad.pack(fill="x")
        StepHeader(pad, "2", "Thiet lap lop",
                   "(Chi lam 1 lan cho moi lop - cac thang sau chi can Buoc 1)",
                   num_bg=C_STEP2_BG).pack(anchor="w", pady=(0, 12))
        action_row = tk.Frame(pad, bg=C_CARD)
        action_row.pack(fill="x")
        FlatButton(action_row,
                   text="THIET LAP MAU LOP...",
                   bg_color=C_STEP2_BG, hover_color=C_PRIMARY_ACT,
                   text_color="#FFFFFF", font_spec=(FONT, 10, "bold"),
                   px=16, py=8, command=self.save_template
                   ).pack(side="left", padx=(0, 16))
        tk.Label(action_row,
                 text="Chon file Excel mau hanh kiem de he thong ghi nho\ndanh sach, si so va diem nen ban dau.",
                 font=(FONT, 9), fg=C_TEXT_MUTED, bg=C_CARD,
                 justify="left").pack(side="left", anchor="w")

    def _build_step3(self, parent):
        card = self._make_card(parent, accent=C_CTA)
        inner = card.inner
        pad = tk.Frame(inner, bg=C_CARD, padx=20, pady=18)
        pad.pack(fill="x")
        StepHeader(pad, "3", "Tong hop ket qua",
                   num_bg=C_STEP3_BG).pack(anchor="w", pady=(0, 6))
        tk.Label(pad,
                 text="He thong tu dong nhan dien lop, doc VnEdu, doi chieu tieu chi, chong trung lap hanh vi, "
                      "ap tran diem cong va lap danh sach muc can GVCN xac nhan.",
                 font=(FONT, 9), fg=C_TEXT_MUTED, bg=C_CARD,
                 wraplength=860, justify="left"
                 ).pack(anchor="w", pady=(0, 14))
        cta_row = tk.Frame(pad, bg=C_CARD)
        cta_row.pack(fill="x", pady=(0, 12))
        self.btn_run = FlatButton(
            cta_row,
            text="   TONG HOP   ",
            bg_color=C_CTA, hover_color=C_CTA_HOV,
            text_color="#FFFFFF", font_spec=(FONT, 13, "bold"),
            px=32, py=12, command=self.start_pipeline_thread
        )
        self.btn_run.pack(side="left", padx=(0, 20))
        self.status_badge = StatusBadge(cta_row, bg=C_CARD)
        self.status_badge.pack(side="left", anchor="w")
        self.progress_bar = ttk.Progressbar(
            pad, style="Teal.Horizontal.TProgressbar", mode="indeterminate"
        )
        self.progress_bar.pack(fill="x")

    def _make_stat(self, parent, label, value, bg, fg):
        box = tk.Frame(parent, bg=bg,
                       highlightbackground=C_CARD_BORDER, highlightthickness=1,
                       padx=12, pady=10)
        tk.Label(box, text=label, font=(FONT, 8), fg=C_TEXT_MUTED, bg=bg
                 ).pack(anchor="center")
        lbl = tk.Label(box, text=value, font=(FONT, 18, "bold"), fg=fg, bg=bg)
        lbl.pack(anchor="center", pady=(2, 0))
        box.val_label = lbl
        return box

    def _build_result_dashboard(self, parent):
        self.result_card = tk.Frame(parent, bg=C_CARD)
        tk.Frame(self.result_card, bg=C_SUCCESS, height=3).pack(fill="x")
        inner = tk.Frame(self.result_card, bg=C_CARD, padx=20, pady=16)
        inner.pack(fill="x")
        tk.Label(inner,
                 text="Ket qua tong hop hoan tat",
                 font=(FONT, 12, "bold"), fg=C_SUCCESS_TXT, bg=C_CARD
                 ).pack(anchor="w", pady=(0, 12))
        stat_row = tk.Frame(inner, bg=C_CARD)
        stat_row.pack(fill="x", pady=(0, 12))
        self.stat_students     = self._make_stat(stat_row, "Hoc sinh", "0", C_STAT_B_BG, C_STAT_B_TXT)
        self.stat_transactions = self._make_stat(stat_row, "Giao dich", "0", C_STAT_G_BG, C_STAT_G_TXT)
        self.stat_reviews      = self._make_stat(stat_row, "Can GVCN xac nhan", "0", C_STAT_O_BG, C_STAT_O_TXT)
        self.stat_duplicates   = self._make_stat(stat_row, "Trung da bo", "0", C_STAT_S_BG, C_STAT_S_TXT)
        for s in (self.stat_students, self.stat_transactions, self.stat_reviews):
            s.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.stat_duplicates.pack(side="left", fill="both", expand=True)
        fbox = tk.Frame(inner, bg=C_BG_ALT, padx=14, pady=10)
        fbox.pack(fill="x", pady=(0, 10))
        self.lbl_result_file = tk.Label(
            fbox, text="File ket qua: (chua co)",
            font=(FONT, 9), fg=C_TEXT_BODY, bg=C_BG_ALT,
            anchor="w", wraplength=800, justify="left"
        )
        self.lbl_result_file.pack(fill="x", pady=(0, 8))
        btn_r = tk.Frame(fbox, bg=C_BG_ALT)
        btn_r.pack(fill="x")
        FlatButton(btn_r, text="Mo file Excel ket qua",
                   bg_color=C_SUCCESS, hover_color=C_SUCCESS_HOV,
                   font_spec=(FONT, 10, "bold"), px=14, py=8,
                   command=self.open_output_file
                   ).pack(side="left", padx=(0, 10))
        FlatButton(btn_r, text="Mo thu muc ket qua",
                   bg_color=C_PRIMARY, hover_color=C_PRIMARY_HOV,
                   font_spec=(FONT, 10), px=14, py=8,
                   command=self.open_output_folder
                   ).pack(side="left")

    def _build_log(self, parent):
        log_wrap = tk.Frame(parent, bg=C_BG)
        log_wrap.pack(fill="both", expand=True, pady=(8, 0))
        hdr = tk.Frame(log_wrap, bg=C_BG)
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(hdr, text="Nhat ky hoat dong",
                 font=(FONT, 9, "bold"), fg=C_TEXT_MUTED, bg=C_BG
                 ).pack(side="left")
        tk.Button(hdr, text="Xoa nhat ky",
                  font=(FONT, 8), fg=C_TEXT_MUTED, bg=C_BG,
                  relief="flat", bd=0, cursor="hand2",
                  command=self._clear_log
                  ).pack(side="right")
        log_frame = tk.Frame(log_wrap, bg=C_CARD,
                             highlightbackground=C_CARD_BORDER, highlightthickness=1)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_frame, height=6, bg=C_CARD, fg=C_TEXT_MUTED,
            font=("Consolas" if sys.platform.startswith("win") else "Courier", 9),
            relief="flat", bd=0, padx=10, pady=8, wrap="word",
            insertbackground=C_PRIMARY,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        vsb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=vsb.set)

    def _log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {message}\n")
        self.log_text.see("end")

    def _clear_log(self):
        self.log_text.delete("1.0", "end")

    def choose_vnedu_file(self):
        initial = self.source_var.get()
        initial_dir = str(Path(initial).parent) if Path(initial).is_file() else initial
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(ROOT)
        value = filedialog.askopenfilename(
            title="Chon file bao cao chi tiet VnEdu (.xlsx hoac .xls)",
            initialdir=initial_dir,
            filetypes=[("Bao cao Excel VnEdu", "*.xlsx *.xls"), ("Tat ca tep", "*.*")],
        )
        if value:
            self.source_var.set(value)
            self._log(f"Da chon file VnEdu: {Path(value).name}")
            self.status_badge.set_state("ready", f"\u25cf Da chon: {Path(value).name}")

    def choose_source_dir(self):
        initial = self.source_var.get()
        if not initial or not Path(initial).exists():
            initial = str(ROOT)
        value = filedialog.askdirectory(title="Chon thu muc chua du lieu thang",
                                        initialdir=initial)
        if value:
            self.source_var.set(value)
            self._log(f"Da chon thu muc nguon: {Path(value).name}")
            self.status_badge.set_state("ready", f"\u25cf Da chon thu muc: {Path(value).name}")

    def choose_output_dir(self):
        initial = self.output_var.get()
        if not initial or not Path(initial).exists():
            initial = str(ROOT)
        value = filedialog.askdirectory(title="Chon thu muc luu ket qua tong hop",
                                        initialdir=initial)
        if value:
            self.output_var.set(value)
            self._log(f"Da chon thu muc luu: {value}")

    def save_template(self):
        value = filedialog.askopenfilename(
            title="Chon file Excel mau hanh kiem cua lop",
            initialdir=str(ROOT),
            filetypes=[("File Excel", "*.xlsx")],
        )
        if not value:
            return
        try:
            self._log(f"Dang thiet lap mau lop tu file: {Path(value).name}...")
            destination, profile, students = save_class_template(value, ROOT)
            self._log(f"Thiet lap thanh cong mau lop {profile.class_name} ({len(students)} hoc sinh).")
            messagebox.showinfo(
                "Da thiet lap mau lop thanh cong",
                f"Da luu ban sao mau lop: {profile.class_name}\n"
                f"Si so nhan dien: {len(students)} hoc sinh.\n\n"
                f"Tu cac thang tiep theo, Thay/Co chi can chon file VnEdu o Buoc 1.\n\n"
                f"Vi tri luu: {destination}",
            )
        except Exception as exc:
            self._log(f"Loi thiet lap mau lop: {exc}")
            messagebox.showerror(
                "Khong the thiet lap mau lop",
                f"He thong khong the doc file mau nay:\n{exc}\n\n"
                "Vui long kiem tra file Excel co dung dinh dang mau danh gia hanh kiem cua lop hay khong."
            )

    def start_pipeline_thread(self):
        if self.is_running:
            return
        source = self.source_var.get().strip()
        output = self.output_var.get().strip()
        if not source:
            messagebox.showwarning(
                "Chua chon du lieu",
                "Thay/Co chua chon file hoac thu muc du lieu nguon.\n\n"
                "Vui long bam 'Chon file VnEdu...' hoac 'Chon thu muc...' o Buoc 1."
            )
            return
        if not Path(source).exists():
            messagebox.showerror(
                "Duong dan khong ton tai",
                f"Khong tim thay file hoac thu muc nguon tai:\n{source}\n\n"
                "Vui long kiem tra lai duong dan da chon hoac di chuyen file ve dung vi tri."
            )
            return
        if not output:
            output = str(ROOT / "outputs")
            self.output_var.set(output)
        self.is_running = True
        self.btn_run.configure(state="disabled", text="   DANG XU LY...   ")
        self.btn_run.set_colors("#94A3B8", "#94A3B8")
        self.progress_bar.configure(style="Orange.Horizontal.TProgressbar")
        self.progress_bar.start(12)
        self.status_badge.set_state("running")
        self.config(cursor="wait")
        try:
            self.result_card.pack_forget()
        except Exception:
            pass
        self._log(f"Bat dau tong hop tu: {Path(source).name}")
        threading.Thread(target=self._worker_run, args=(source, output), daemon=True).start()

    def _worker_run(self, source, output):
        try:
            t0 = time.time()
            result = run_pipeline(source, output)
            elapsed = time.time() - t0
            self.after(0, self._on_success, result, elapsed)
        except Exception as exc:
            tb = traceback.format_exc()
            self.after(0, self._on_error, exc, tb)

    def _on_success(self, result: RunResult, elapsed: float):
        self.is_running = False
        self.progress_bar.stop()
        self.progress_bar.configure(style="Teal.Horizontal.TProgressbar")
        self.btn_run.configure(state="normal", text="   TONG HOP   ")
        self.btn_run.set_colors(C_CTA, C_CTA_HOV)
        self.config(cursor="")
        self.latest_result = result
        self.stat_students.val_label.configure(text=str(result.student_count))
        self.stat_transactions.val_label.configure(text=str(result.transaction_count))
        self.stat_reviews.val_label.configure(text=str(result.review_count))
        self.stat_duplicates.val_label.configure(text=str(result.duplicate_count))
        out_name = Path(result.output_file).name
        self.lbl_result_file.configure(
            text=f"File ket qua: {out_name}\nDuong dan: {result.output_file}"
        )
        self.result_card.pack(fill="x", pady=(0, 14))
        status_msg = (
            f"Hoan tat ({elapsed:.1f}s) - {result.student_count} hoc sinh, "
            f"{result.transaction_count} giao dich, "
            f"{result.review_count} muc can GVCN xac nhan."
        )
        self.status_badge.set_state("success", f"\u2713 {status_msg}")
        self._log(f"Tong hop thanh cong ({elapsed:.1f}s). File xuat: {out_name}")
        if result.review_count > 0:
            self._log(f"Luu y: Co {result.review_count} muc can GVCN xac nhan tai sheet 'CAN_GVCN_XAC_NHAN'.")
        messagebox.showinfo(
            "Tong hop hoan tat",
            f"Da hoan tat tong hop du lieu!\n\n"
            f"So hoc sinh: {result.student_count}\n"
            f"Tong giao dich: {result.transaction_count}\n"
            f"Giao dich trung da xu ly: {result.duplicate_count}\n"
            f"Muc can GVCN xac nhan: {result.review_count}\n\n"
            f"File ket qua:\n{result.output_file}\n\n"
            "Thay/Co hay kiem tra sheet 'CAN_GVCN_XAC_NHAN' truoc khi su dung chinh thuc."
        )

    def _on_error(self, exc: Exception, tb_str: str):
        self.is_running = False
        self.progress_bar.stop()
        self.progress_bar.configure(style="Teal.Horizontal.TProgressbar")
        self.btn_run.configure(state="normal", text="   TONG HOP   ")
        self.btn_run.set_colors(C_CTA, C_CTA_HOV)
        self.config(cursor="")
        log_file = ROOT / "work" / "loi_he_thong.txt"
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text(tb_str, encoding="utf-8")
            log_note = f"\n\nChi tiet ky thuat da luu tai:\n{log_file}"
        except Exception:
            log_note = ""
        err_text = str(exc)
        self._log(f"LOI: {err_text}")
        self.status_badge.set_state("error", f"\u2715 Loi: {err_text[:80]}")
        if isinstance(exc, PermissionError) or any(
            kw in err_text for kw in ("Permission denied", "[Errno 13]")
        ):
            messagebox.showerror(
                "File Excel dang mo",
                "File Excel ket qua dang duoc mo trong Microsoft Excel hoac mot chuong trinh khac.\n\n"
                "Huong dan xu ly:\n"
                "1. Thay/Co vui long DONG file Excel do lai tren thanh tac vu.\n"
                "2. Sau do bam 'TONG HOP' de he thong xuat lai file."
                f"{log_note}"
            )
        elif any(kw in err_text.lower() for kw in ("chua co mau", "khong tim thay mau", "no template")):
            messagebox.showerror(
                "Chua co mau lop",
                f"{err_text}\n\n"
                "Huong dan xu ly:\n"
                "1. Bam nut 'THIET LAP MAU LOP' o Buoc 2.\n"
                "2. Chon file Excel mau hanh kiem chuan cua lop.\n"
                "3. Sau do bam 'TONG HOP' lai."
                f"{log_note}"
            )
        else:
            messagebox.showerror(
                "Co loi xay ra",
                f"He thong gap su co trong qua trinh xu ly:\n{err_text}\n\n"
                "Huong dan xu ly:\n"
                "- Kiem tra xem file bao cao VnEdu co dang mo hoac bi khoa hay khong.\n"
                "- Dam bao file dung dinh dang bao cao nen nep / hanh kiem."
                f"{log_note}"
            )

    def open_output_file(self):
        if not self.latest_result or not self.latest_result.output_file:
            messagebox.showinfo("Thong bao", "Chua co file ket qua de mo.")
            return
        file_path = Path(self.latest_result.output_file)
        if not file_path.exists():
            messagebox.showerror("Khong tim thay file", f"File khong ton tai tai:\n{file_path}")
            return
        try:
            os.startfile(str(file_path))
            self._log(f"Da mo file Excel: {file_path.name}")
        except Exception as exc:
            messagebox.showerror("Khong the mo file", f"Loi khi mo file Excel:\n{exc}")

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
            self._log(f"Da mo thu muc: {folder}")
        except Exception as exc:
            messagebox.showerror("Khong the mo thu muc", f"Loi khi mo thu muc:\n{exc}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
