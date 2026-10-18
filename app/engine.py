from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from docx import Document
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

try:
    import xlrd
except ImportError:  # The packaged installer supplies xlrd for old VnEdu .xls reports.
    xlrd = None


DEFAULT_BASE_SCORE = 80.0
DEFAULT_BONUS_CAP = 10.0
COPYRIGHT = "Bản quyền © Tuyên Bùi"
RULES_FILE = "TIEU_CHI_HANH_KIEM.xlsx"
CLASS_PROFILES_DIR = "ho_so_lop"


def compact_spaces(value: object) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def fold(value: object) -> str:
    text = compact_spaces(value).lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def normalize_class(value: object) -> str:
    """Normalize class labels without assuming any particular grade or class."""
    text = re.sub(r"[^A-Z0-9]", "", fold(value).upper())
    match = re.search(r"(\d+)([A-Z]+)0*(\d+)", text)
    if match:
        return f"{match.group(1)}{match.group(2)}{int(match.group(3))}"
    return text


def display_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(value, 2)


def display_points_vn(value: float) -> str:
    """Display conduct points in the Vietnamese decimal style used in the template."""
    return str(display_number(value)).replace(".", ",")


def content_without_trailing_points(content: str) -> str:
    """Avoid repeating an old source score before showing the applied rule score."""
    return re.sub(r"\s*\(\s*[+-]?\s*\d+(?:[.,]\d+)?\s*(?:điểm|diem)?\s*\)\s*$", "", compact_spaces(content))


def format_deduction_line(content: str, points: float) -> str:
    return f"- {content_without_trailing_points(content)} (-{display_points_vn(points)})"


def format_improvement_line(content: str, points: float) -> str:
    """Show every recorded improvement item; only show a score when one applies."""
    if points > 0:
        return format_deduction_line(content, points)
    return f"- {content_without_trailing_points(content)}"


def is_absence_note(note: object) -> bool:
    """True only for an absence, whether it is permitted or unpermitted.

    Being late is intentionally not included.  The weekly bonus policy only
    removes the three weekly baseline items when the student is absent.
    """
    normalized = fold(note)
    absence_markers = (
        "vang",
        "nghi hoc",
        "nghi phep",
        "co phep",
        "khong phep",
    )
    return any(marker in normalized for marker in absence_markers)


def is_uniform_only_note(note: object) -> bool:
    """Identify a conduct/uniform issue that must not reduce study or attendance."""
    normalized = fold(note)
    uniform_markers = ("phu hieu", "dong phuc", "trang diem", "son moi", "mang son")
    other_weekly_issues = (
        "vang", "nghi hoc", "tre", "ve som", "khong hoc bai", "khong lam bai", "chua lam bai",
        "khong nop bai", "khong mang sach", "khong mang vo",
    )
    return any(marker in normalized for marker in uniform_markers) and not any(
        marker in normalized for marker in other_weekly_issues
    )


def parse_date(value: object) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = compact_spaces(value)
    if not text:
        return ""
    for pattern in (r"(\d{1,2})/(\d{1,2})/(\d{4})", r"(\d{1,2})/(\d{1,2})"):
        match = re.search(pattern, text)
        if match:
            day, month = int(match.group(1)), int(match.group(2))
            year = int(match.group(3)) if match.lastindex == 3 else 2026
            return f"{year:04d}-{month:02d}-{day:02d}"
    return text


@dataclass
class Student:
    student_id: str
    stt: int
    name: str
    class_name: str
    aliases: list[str]


@dataclass
class Transaction:
    transaction_id: str
    student_id: str
    student_name: str
    class_name: str
    event_date: str
    source_file: str
    source_location: str
    raw_content: str
    normalized_content: str
    kind: str
    rule_code: str
    proposed_points: float | None
    applied_points: float
    status: str
    evidence: str
    dedupe_key: str
    note: str = ""


@dataclass
class ReviewItem:
    review_id: str
    source_file: str
    source_location: str
    raw_name: str
    class_name: str
    raw_content: str
    reason: str
    suggested_student: str = ""
    suggested_rule: str = ""


@dataclass
class RunResult:
    output_file: str
    student_count: int
    transaction_count: int
    review_count: int
    duplicate_count: int
    source_files: list[str]


@dataclass
class ClassProfile:
    class_name: str
    sheet_name: str
    base_score: float
    bonus_cap: float
    period: str


DEDUCTION_RULES = [
    ("TRU_025_PHU_HIEU", 0.25, ["khong phu hieu", "sai phu hieu", "khong deo phu hieu", "khong phu heu"]),
    ("TRU_100_DI_TRE", 1.0, ["tre sang", "di hoc tre"]),
    ("TRU_100_DIEN_THOAI", 1.0, ["mang dtd d", "mang dtdd", "dem dien thoai", "mang dien thoai"]),
    ("TRU_100_TRANG_DIEM", 1.0, ["mang son", "to son", "son moi", "trang diem"]),
    ("TRU_100_SAI_DONG_PHUC", 1.0, ["sai dong phuc"]),
    ("TRU_200_NGHI_KHONG_PHEP", 2.0, ["nghi hoc khong phep", "vang khong phep"]),
]


ACTIVITY_RULES = [
    ("CONG_100_VAN_NGHE", 1.0, ["tham gia van nghe", "van nghe"]),
    ("CONG_100_LE_TAN", 1.0, ["le tan", "hop phhs"]),
    ("CONG_100_THU_VIEN", 1.0, ["thu vien", "xep sach", "trang tri duong sach"]),
    ("CONG_100_TRAM", 1.0, ["dung tram", "lam san pham tram"]),
]


def criteria_keywords(value: object) -> list[str]:
    """Create conservative matching phrases from a formal criterion description."""
    normalized = fold(value)
    candidates = {normalized}
    for part in re.split(r"[,;:.()]|\bva\b|\bhoac\b", normalized):
        tokens = part.split()
        if len(tokens) >= 3:
            candidates.add(" ".join(tokens))
            candidates.add(" ".join(tokens[:min(5, len(tokens))]))
    return sorted(x for x in candidates if len(x.split()) >= 3)


def heading_points(value: object, kind: str) -> float | None:
    text = compact_spaces(value).lower().replace(",", ".")
    marker = "cộng" if kind == "CONG" else "trừ"
    marker_plain = "cong" if kind == "CONG" else "tru"
    match = re.search(rf"(?:{marker}|{marker_plain}).*?(\d+(?:\.\d+)?)\s*(?:điểm|diem)", text)
    return float(match.group(1)) if match else None


def load_criteria_rules(project_root: Path) -> tuple[list[tuple[str, float, list[str]]], list[tuple[str, str, float, str]]]:
    """Read the editable master criteria file kept outside each monthly source folder."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        path = Path(sys._MEIPASS) / "quy_tac" / RULES_FILE
    else:
        path = project_root / "quy_tac" / RULES_FILE
    if not path.exists():
        return [], []
    wb = load_workbook(path, data_only=True, read_only=True)
    rules: list[tuple[str, float, list[str]]] = []
    report_rows: list[tuple[str, str, float, str]] = []
    current_points = {"CONG": None, "TRU": None}
    try:
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                stt, bonus_text, deduction_text = row[:3]
                for kind, text in (("CONG", bonus_text), ("TRU", deduction_text)):
                    points = heading_points(text, kind)
                    if points is not None:
                        current_points[kind] = points
                    item_number = compact_spaces(stt)
                    if item_number and "." not in item_number and points is None:
                        # A new unscored section (for example "lưu ý") ends the preceding score group.
                        current_points[kind] = None
                    if not item_number or "." not in item_number or not compact_spaces(text):
                        continue
                    if current_points[kind] is None:
                        continue
                    code = f"TC_{kind}_{item_number.replace('.', '_').replace(' ', '')}"
                    phrases = criteria_keywords(text)
                    if not phrases:
                        continue
                    rules.append((code, float(current_points[kind]), phrases))
                    report_rows.append((code, "CỘNG" if kind == "CONG" else "TRỪ", float(current_points[kind]), compact_spaces(text)))
    finally:
        wb.close()
    return rules, report_rows


def rule_for(content: str, kind: str, criteria_rules: list[tuple[str, float, list[str]]] | None = None):
    normalized = fold(content)
    built_in = DEDUCTION_RULES if kind == "TRU" else ACTIVITY_RULES
    rules = [rule for rule in (criteria_rules or []) if rule[0].startswith(f"TC_{kind}_")] + built_in
    for code, points, phrases in rules:
        if any(fold(phrase) in normalized for phrase in phrases):
            return code, points
    return "", None


def make_id(prefix: str, *parts: object) -> str:
    raw = "|".join(compact_spaces(x) for x in parts)
    return f"{prefix}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12].upper()}"


def find_file(folder: Path, predicate) -> Path | None:
    return next((p for p in folder.iterdir() if p.is_file() and predicate(p)), None)


def find_header_row(ws, required_headers: Iterable[str], limit: int = 20) -> tuple[int, dict[str, int]] | None:
    """Find a report table by header labels instead of a fixed row/column position."""
    required = {fold(header) for header in required_headers}
    for row in range(1, min(ws.max_row, limit) + 1):
        columns = {
            fold(ws.cell(row, col).value): col
            for col in range(1, min(ws.max_column, 30) + 1)
            if fold(ws.cell(row, col).value)
        }
        if required.issubset(columns):
            return row, columns
    return None


def is_vnedu_violation_workbook(path: Path) -> bool:
    """Recognize the VnEdu detailed conduct report from its columns, not its file name."""
    if path.suffix.lower() != ".xlsx":
        return False
    try:
        wb = load_workbook(path, data_only=True, read_only=True)
        try:
            return any(
                find_header_row(ws, ("Họ và tên", "Lớp", "Hình thức", "Ngày")) is not None
                for ws in wb.worksheets
            )
        finally:
            wb.close()
    except Exception:
        return False


def find_xls_header_row(ws, required_headers: Iterable[str], limit: int = 20) -> tuple[int, dict[str, int]] | None:
    """Find the VnEdu table in a legacy .xls worksheet (zero-based columns)."""
    required = {fold(header) for header in required_headers}
    for row in range(min(ws.nrows, limit)):
        columns = {
            fold(ws.cell_value(row, col)): col
            for col in range(min(ws.ncols, 30))
            if fold(ws.cell_value(row, col))
        }
        if required.issubset(columns):
            return row, columns
    return None


def parse_xls_date(book, ws, row: int, col: int) -> str:
    value = ws.cell_value(row, col)
    if xlrd is not None and ws.cell_type(row, col) == xlrd.XL_CELL_DATE:
        return parse_date(xlrd.xldate_as_datetime(value, book.datemode))
    return parse_date(value)


def is_vnedu_violation_xls(path: Path) -> bool:
    """Recognize a legacy VnEdu report without asking Microsoft Excel to open it."""
    if path.suffix.lower() != ".xls" or xlrd is None:
        return False
    try:
        book = xlrd.open_workbook(path, ignore_workbook_corruption=True)
        return any(
            find_xls_header_row(ws, ("Họ và tên", "Lớp", "Hình thức", "Ngày")) is not None
            for ws in book.sheets()
        )
    except Exception:
        return False


def vnedu_class_and_period(path: Path) -> tuple[str, str]:
    """Read the class and reporting month from a VnEdu detailed report."""
    wb = load_workbook(path, data_only=True, read_only=True)
    classes: set[str] = set()
    periods: list[str] = []
    try:
        for ws in wb.worksheets:
            header = find_header_row(ws, ("Họ và tên", "Lớp", "Hình thức", "Ngày"))
            if not header:
                continue
            header_row, columns = header
            class_col = columns[fold("Lớp")]
            form_col = columns[fold("Hình thức")]
            date_col = columns[fold("Ngày")]
            inherited_class = ""
            for row in range(header_row + 1, ws.max_row + 1):
                stated_class = normalize_class(ws.cell(row, class_col).value)
                if stated_class:
                    inherited_class = stated_class
                if not compact_spaces(ws.cell(row, form_col).value) or not inherited_class:
                    continue
                classes.add(inherited_class)
                event_date = parse_date(ws.cell(row, date_col).value)
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date):
                    periods.append(event_date[:7])
    finally:
        wb.close()
    if len(classes) != 1:
        class_text = ", ".join(sorted(classes)) or "không xác định"
        raise ValueError(f"Báo cáo VnEdu phải chỉ có một lớp. Lớp phát hiện: {class_text}")
    return next(iter(classes)), Counter(periods).most_common(1)[0][0] if periods else ""


def vnedu_xls_class_and_period(path: Path) -> tuple[str, str]:
    """Read class and month from a legacy VnEdu .xls report."""
    if xlrd is None:
        raise RuntimeError("Thiếu thư viện đọc Excel .xls; hãy chạy CAI_DAT_VA_CHAY.cmd một lần")
    book = xlrd.open_workbook(path, ignore_workbook_corruption=True)
    classes: set[str] = set()
    periods: list[str] = []
    for ws in book.sheets():
        header = find_xls_header_row(ws, ("Họ và tên", "Lớp", "Hình thức", "Ngày"))
        if not header:
            continue
        header_row, columns = header
        class_col = columns[fold("Lớp")]
        form_col = columns[fold("Hình thức")]
        date_col = columns[fold("Ngày")]
        inherited_class = ""
        for row in range(header_row + 1, ws.nrows):
            stated_class = normalize_class(ws.cell_value(row, class_col))
            if stated_class:
                inherited_class = stated_class
            if not compact_spaces(ws.cell_value(row, form_col)) or not inherited_class:
                continue
            classes.add(inherited_class)
            event_date = parse_xls_date(book, ws, row, date_col)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date):
                periods.append(event_date[:7])
    if len(classes) != 1:
        class_text = ", ".join(sorted(classes)) or "không xác định"
        raise ValueError(f"Báo cáo VnEdu phải chỉ có một lớp. Lớp phát hiện: {class_text}")
    return next(iter(classes)), Counter(periods).most_common(1)[0][0] if periods else ""


def find_violation_files(folder: Path) -> list[Path]:
    """Find both the original consolidated report and VnEdu detailed reports."""
    files: list[Path] = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        name = fold(path.name)
        if suffix == ".xlsx" and ("vi pham" in name or is_vnedu_violation_workbook(path)):
            files.append(path)
        elif suffix == ".xls" and any(token in name for token in ("vi pham", "vnedu", "bao cao ne nep", "bao cao nen nep")):
            # Excel .xls reports are converted to a temporary .xlsx copy before reading.
            files.append(path)
    return files


def template_info_for_file(path: Path) -> tuple[Path, str] | None:
    """Recognize one output template by its columns, rather than its file name."""
    if not path.is_file() or path.suffix.lower() != ".xlsx":
        return None
    try:
        wb = load_workbook(path, data_only=True, read_only=True)
        try:
            for ws in wb.worksheets:
                headers = [fold(ws.cell(1, col).value) for col in range(1, min(ws.max_column, 20) + 1)]
                has_stt = any(header == "stt" for header in headers)
                has_name = any("ho va ten" in header for header in headers)
                has_class = any(header == "lop" for header in headers)
                has_result = any("tong diem" in header or "xep loai" in header for header in headers)
                if has_stt and has_name and has_class and has_result:
                    return path, ws.title
        finally:
            wb.close()
    except Exception:
        return None
    return None


def find_template_file(folder: Path) -> tuple[Path, str] | None:
    """Find an output template by its columns, rather than by a class-specific file name."""
    for path in sorted(folder.iterdir()):
        info = template_info_for_file(path)
        if info:
            return info
    return None


def saved_class_template(project_root: Path, class_name: str) -> tuple[Path, str] | None:
    """Return the one-time saved template for a class, if it has been set up."""
    profile_root = project_root / CLASS_PROFILES_DIR
    if not profile_root.is_dir():
        return None
    for path in sorted(profile_root.rglob("*.xlsx")):
        info = template_info_for_file(path)
        if not info:
            continue
        try:
            _, profile = load_students(*info)
        except Exception:
            continue
        if profile.class_name == class_name:
            return info
    return None


def save_class_template(template_path: str | Path, project_root: Path) -> tuple[Path, ClassProfile, list[Student]]:
    """Copy a class template once; future monthly runs only need the VnEdu file."""
    info = template_info_for_file(Path(template_path).resolve())
    if not info:
        raise ValueError("File được chọn không phải mẫu hạnh kiểm/rèn luyện hợp lệ")
    students, profile = load_students(*info)
    destination = project_root / CLASS_PROFILES_DIR / profile.class_name / "MAU_HANH_KIEM.xlsx"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(info[0], destination)
    return destination, profile, students


def find_weekly_file(folder: Path) -> Path | None:
    """Identify the weekly score workbook from its sheets, not its file name."""
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".xlsx":
            continue
        try:
            wb = load_workbook(path, data_only=True, read_only=True)
            if any("xet tuan" in fold(ws.title) for ws in wb.worksheets):
                wb.close()
                return path
            wb.close()
        except Exception:
            continue
    return None


def infer_period(template_path: Path, sheet_name: str) -> str:
    """Use a month stated in the template name/sheet when available; otherwise use this month."""
    text = fold(f"{template_path.stem} {sheet_name}")
    match = re.search(r"thang\s*(\d{1,2})", text)
    month = int(match.group(1)) if match else datetime.now().month
    year_match = re.search(r"\b(20\d{2})\b", template_path.stem)
    year = int(year_match.group(1)) if year_match else datetime.now().year
    return f"{year:04d}-{month:02d}"


def locate_source_folder(selected: Path) -> Path:
    """Accept the month folder, project folder, outputs folder, or an extracted package folder."""
    if selected.is_file():
        return selected.parent.resolve()
    candidates = []
    for base in [selected, *list(selected.parents)[:3]]:
        candidates.extend([base, base / "work" / "month_09", base / "sources_original"])
    seen = set()
    for candidate in candidates:
        try:
            key = str(candidate.resolve())
        except OSError:
            key = str(candidate)
        if key in seen or not candidate.is_dir():
            continue
        seen.add(key)
        files = [p for p in candidate.iterdir() if p.is_file()]
        has_template = find_template_file(candidate) is not None
        has_monthly = find_weekly_file(candidate) is not None
        has_violations = bool(find_violation_files(candidate))
        if has_template and has_monthly and has_violations:
            return candidate.resolve()
    return selected.resolve()


def load_students(template_path: Path, sheet_name: str) -> tuple[list[Student], ClassProfile]:
    wb = load_workbook(template_path, data_only=True, read_only=True)
    ws = wb[sheet_name]
    students = []
    classes = set()
    totals = []
    for row in range(2, ws.max_row + 1):
        stt, name, class_name = ws.cell(row, 1).value, ws.cell(row, 2).value, ws.cell(row, 3).value
        if not stt or not name:
            continue
        name = compact_spaces(name)
        normalized_class = normalize_class(class_name)
        if not normalized_class:
            raise ValueError(f"Thiếu lớp của học sinh tại dòng {row} trong file mẫu")
        classes.add(normalized_class)
        aliases = {fold(name)}
        tokens = fold(name).split()
        if len(tokens) >= 2:
            aliases.add(" ".join(tokens[-2:]))
        students.append(Student(f"{normalized_class}-{int(stt):03d}", int(stt), name, normalized_class, sorted(aliases)))
        total_value = ws.cell(row, 8).value
        if isinstance(total_value, (int, float)):
            totals.append(float(total_value))
    if not students:
        wb.close()
        raise ValueError("File mẫu không có học sinh nào ở các cột STT, Họ tên, Lớp")
    if len(classes) != 1:
        wb.close()
        raise ValueError("File mẫu phải chỉ chứa một lớp; hãy chọn mẫu riêng cho từng lớp")
    base_score = totals[0] if totals else DEFAULT_BASE_SCORE
    profile = ClassProfile(classes.pop(), sheet_name, base_score, DEFAULT_BONUS_CAP, infer_period(template_path, sheet_name))
    wb.close()
    return students, profile


def match_student(raw_name: object, students: list[Student]) -> tuple[Student | None, str, list[Student]]:
    key = fold(raw_name)
    if not key:
        return None, "empty", []
    exact = [s for s in students if key == fold(s.name)]
    if len(exact) == 1:
        return exact[0], "exact", exact
    alias = [s for s in students if key in s.aliases]
    if len(alias) == 1:
        return alias[0], "unique_alias", alias
    suffix = [s for s in students if fold(s.name).endswith(key) or key.endswith(fold(s.name))]
    if len(suffix) == 1:
        return suffix[0], "unique_suffix", suffix
    candidates = alias or suffix
    return None, "ambiguous" if candidates else "not_found", candidates


def extract_weekly_transactions(path: Path, students: list[Student], profile: ClassProfile, criteria_rules=None):
    wb_values = load_workbook(path, data_only=True, read_only=True)
    transactions: list[Transaction] = []
    reviews: list[ReviewItem] = []
    for ws in wb_values.worksheets:
        if not ws.title.startswith("XET TUAN"):
            continue
        week_match = re.search(r"TUAN\s*0?(\d+)", fold(ws.title).upper())
        week = int(week_match.group(1)) if week_match else 0
        if "DIEM CONG" in ws.title:
            deduction_title = ws.title.replace("DIEM CONG-TONG", "DIEM TRU")
            deduction_ws = wb_values[deduction_title] if deduction_title in wb_values.sheetnames else None
            point_columns = {
                9: (0.5, "Có tiến bộ hoặc chủ động giúp đỡ bạn", "CONG_050_TIEN_BO"),
                10: (0.5, "Hoàn thành nhiệm vụ lớp hoặc cán sự", "CONG_050_NHIEM_VU"),
                12: (1.0, "Phối hợp tốt hoặc đại diện trường tham gia hoạt động", "CONG_100_PHOI_HOP"),
                13: (1.0, "Tổ chức hoạt động hoặc có đóng góp tích cực", "CONG_100_TO_CHUC"),
                14: (1.0, "Bảo vệ môi trường và mỹ quan", "CONG_100_MOI_TRUONG"),
                16: (2.0, "Cán bộ lớp hoàn thành xuất sắc nhiệm vụ", "CONG_200_CAN_SU"),
                17: (2.0, "Có sáng kiến hoặc đại diện trường tham gia hoạt động", "CONG_200_SANG_KIEN"),
                19: (3.0, "Có sáng kiến hoặc đạt thành tích xuất sắc", "CONG_300_THANH_TICH"),
                20: (3.0, "Có hành động vì cộng đồng hoặc mang danh dự về trường", "CONG_300_CONG_DONG"),
                22: (4.0, "Hành động dũng cảm hoặc thành tích cấp quốc gia", "CONG_400_TIEU_BIEU"),
            }
            for row in range(9, min(ws.max_row, 55) + 1):
                raw_name = ws.cell(row, 2).value
                class_name = normalize_class(ws.cell(row, 3).value)
                if class_name != profile.class_name or not raw_name:
                    continue
                student, match_type, candidates = match_student(raw_name, students)
                if not student:
                    reviews.append(ReviewItem(make_id("RV", path.name, ws.title, row), path.name, f"{ws.title}!R{row}", compact_spaces(raw_name), class_name, "Diem cong tu workbook tuan", f"Ten hoc sinh {match_type}", ", ".join(x.name for x in candidates)))
                    continue
                note = compact_spaces(deduction_ws.cell(row, 4).value) if deduction_ws else ""
                expected_points = float(ws.cell(row, 4).value or 0)
                if expected_points <= 0 and not note:
                    continue
                created: list[Transaction] = []
                base_count = int(ws.cell(row, 6).value or 0)
                attendance_issue = any(word in fold(note) for word in ["tre", "vang", "ve som", "chuyen can"])
                learning_issue = any(word in fold(note) for word in ["khong hoc bai", "khong lam bai", "khong nop bai", "hoc tap"])
                absent = is_absence_note(note)
                uniform_only = is_uniform_only_note(note)
                base_labels = []
                if base_count >= 2:
                    base_labels = [
                        ("Thực hiện tốt học tập", "CONG_025_HOC_TAP"),
                        ("Thực hiện tốt chuyên cần", "CONG_025_CHUYEN_CAN"),
                    ]
                elif base_count == 1:
                    if attendance_issue:
                        base_labels = [("Thực hiện tốt học tập", "CONG_025_HOC_TAP")]
                    elif learning_issue:
                        base_labels = [("Thực hiện tốt chuyên cần", "CONG_025_CHUYEN_CAN")]
                    else:
                        base_labels = [("Thực hiện tốt chuyên cần", "CONG_025_CHUYEN_CAN")]

                source_base_points = min(base_count, 2) * 0.25
                uniform_override_points = 0.0
                if uniform_only and not absent:
                    # A uniform-only issue must affect only tác phong/đồng phục.
                    # The old weekly source may contain F=1, so restore both study
                    # and attendance baseline items without manufacturing a penalty.
                    base_labels = [
                        ("Thực hiện tốt học tập", "CONG_025_HOC_TAP"),
                        ("Thực hiện tốt chuyên cần", "CONG_025_CHUYEN_CAN"),
                    ]
                    uniform_override_points = max(0.0, 0.5 - source_base_points)

                style_count = int(ws.cell(row, 7).value or 0)
                source_style_points = style_count * 0.25
                fixed_style_points = 0.25
                style_adjustment = max(0.0, fixed_style_points - source_style_points) if not absent and not uniform_only else 0.0
                withheld_source_points = 0.0
                absence_note = f"Không cộng vì có vắng học trong tuần: {note}"

                if absent:
                    for index, (label, code) in enumerate(base_labels, 1):
                        withheld_source_points += 0.25
                        created.append(Transaction(make_id("TX", path.name, ws.title, row, code, index), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{ws.title}!F{row}", label, fold(label), "CONG", code, 0.25, 0.0, "KHONG_DU_DIEU_KIEN", f"{ws.title}!F{row}", make_id("DK", student.student_id, f"W{week}", code), absence_note))
                    withheld_source_points += source_style_points
                    label = "Thực hiện tốt tác phong, đồng phục"
                    created.append(Transaction(make_id("TX", path.name, ws.title, row, "STYLE"), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{ws.title}!G{row}", label, fold(label), "CONG", "CONG_025_TAC_PHONG", fixed_style_points, 0.0, "KHONG_DU_DIEU_KIEN", f"{ws.title}!G{row}", make_id("DK", student.student_id, f"W{week}", "STYLE"), absence_note))
                else:
                    for index, (label, code) in enumerate(base_labels, 1):
                        created.append(Transaction(make_id("TX", path.name, ws.title, row, code, index), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{ws.title}!F{row}", label, fold(label), "CONG", code, 0.25, 0.25, "DA_XAC_NHAN", f"{ws.title}!F{row}", make_id("DK", student.student_id, f"W{week}", code)))
                    label = "Thực hiện tốt tác phong, đồng phục"
                    style_status = "KHONG_DU_DIEU_KIEN" if uniform_only else "DA_XAC_NHAN"
                    style_applied = 0.0 if uniform_only else fixed_style_points
                    style_note = "Không cộng do vi phạm tác phong/đồng phục: " + note if uniform_only else ""
                    created.append(Transaction(make_id("TX", path.name, ws.title, row, "STYLE"), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{ws.title}!G{row}", label, fold(label), "CONG", "CONG_025_TAC_PHONG", fixed_style_points, style_applied, style_status, f"{ws.title}!G{row}", make_id("DK", student.student_id, f"W{week}", "STYLE"), style_note))

                source_penalty = float(deduction_ws.cell(row, 5).value or 0) if deduction_ws else 0.0
                if note and source_penalty >= 0:
                    created.append(Transaction(make_id("TX", path.name, ws.title, row, "GHI_NHAN"), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{deduction_ws.title}!D{row}", note, fold(note), "TRU", "GHI_NHAN_HANH_VI", None, 0.0, "GHI_NHAN", f"{deduction_ws.title}!D{row}", make_id("DK", student.student_id, f"W{week}", fold(note)), "Có ghi nhận hành vi nhưng không có điểm trừ trong nguồn"))

                for col, (unit, label, code) in point_columns.items():
                    count = float(ws.cell(row, col).value or 0)
                    if count <= 0:
                        continue
                    points = count * unit
                    created.append(Transaction(make_id("TX", path.name, ws.title, row, code), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{ws.title}!{ws.cell(1, col).column_letter}{row}", label, fold(label), "CONG", code, points, points, "DA_XAC_NHAN", f"{ws.title}!{ws.cell(1, col).column_letter}{row}", make_id("DK", student.student_id, f"W{week}", code)))

                created_total = sum(tx.applied_points for tx in created)
                expected_after_policy = max(0.0, expected_points - withheld_source_points + uniform_override_points + style_adjustment)
                if abs(created_total - expected_after_policy) > 0.001:
                    reviews.append(ReviewItem(make_id("RV", path.name, ws.title, row, "CONG"), path.name, f"{ws.title}!D{row}", compact_spaces(raw_name), class_name, f"Điểm cộng tuần {week}: {expected_after_policy}", f"Không tách khớp chi tiết; đã tách {created_total}", student.name))
                    difference = expected_after_policy - created_total
                    if difference > 0:
                        label = f"Điểm cộng khác tuần {week}"
                        created.append(Transaction(make_id("TX", path.name, ws.title, row, "OTHER"), student.student_id, student.name, profile.class_name, f"{profile.period}-W{week}", path.name, f"{ws.title}!D{row}", label, fold(label), "CONG", "CONG_KHAC", difference, difference, "CHO_GVCN", f"{ws.title}!D{row}", make_id("DK", student.student_id, f"W{week}", "OTHER")))
                transactions.extend(created)
        elif "DIEM TRU" in ws.title:
            for row in range(9, min(ws.max_row, 55) + 1):
                raw_name = ws.cell(row, 2).value
                class_name = normalize_class(ws.cell(row, 3).value)
                if class_name != profile.class_name or not raw_name:
                    continue
                points_raw = float(ws.cell(row, 5).value or 0)
                if points_raw >= 0:
                    continue
                student, match_type, candidates = match_student(raw_name, students)
                content = compact_spaces(ws.cell(row, 4).value) or "Điểm trừ đã có trong workbook tuần"
                if not student:
                    reviews.append(ReviewItem(make_id("RV", path.name, ws.title, row), path.name, f"{ws.title}!R{row}", compact_spaces(raw_name), class_name, content, f"Ten hoc sinh {match_type}", ", ".join(x.name for x in candidates)))
                    continue
                event_date = parse_date(content) or f"{profile.period}-W{week}"
                rule_code, rule_points = rule_for(content, "TRU", criteria_rules)
                points = abs(points_raw)
                dedupe_key = make_id("DK", student.student_id, event_date, fold(content))
                transactions.append(Transaction(make_id("TX", path.name, ws.title, row, "TRU"), student.student_id, student.name, profile.class_name, event_date, path.name, f"{ws.title}!E{row}", content, fold(content), "TRU", rule_code or "TRU_TUAN_CO_SAN", rule_points or points, points, "DA_XAC_NHAN", f"{ws.title}!D{row}:E{row}", dedupe_key, "Dùng điểm đã được GVCN nhập trong workbook tuần"))
    wb_values.close()
    return transactions, reviews


def extract_violation_transactions(path: Path, students: list[Student], profile: ClassProfile, criteria_rules=None):
    wb = load_workbook(path, data_only=True, read_only=True)
    transactions: list[Transaction] = []
    reviews: list[ReviewItem] = []
    for ws in wb.worksheets:
        for row in range(1, ws.max_row + 1):
            raw_name, raw_class = ws.cell(row, 2).value, ws.cell(row, 3).value
            class_name = normalize_class(raw_class)
            if class_name != profile.class_name or not raw_name:
                continue
            event_date = parse_date(ws.cell(row, 4).value)
            content = compact_spaces(ws.cell(row, 5).value)
            if not content:
                continue
            student, match_type, candidates = match_student(raw_name, students)
            if not student:
                reviews.append(ReviewItem(make_id("RV", path.name, ws.title, row), path.name, f"{ws.title}!R{row}", compact_spaces(raw_name), class_name, content, f"Ten hoc sinh {match_type}", ", ".join(x.name for x in candidates)))
                continue
            rule_code, points = rule_for(content, "TRU", criteria_rules)
            if points is None:
                reviews.append(ReviewItem(make_id("RV", path.name, ws.title, row, "RULE"), path.name, f"{ws.title}!R{row}", compact_spaces(raw_name), class_name, content, "Chua co quy tac diem tru ro rang", student.name))
                status, applied = "CHO_GVCN", 0.0
            else:
                status, applied = "DA_XAC_NHAN", points
            dedupe_key = make_id("DK", student.student_id, event_date, fold(content))
            transactions.append(Transaction(make_id("TX", path.name, ws.title, row), student.student_id, student.name, profile.class_name, event_date, path.name, f"{ws.title}!R{row}", content, fold(content), "TRU", rule_code, points, applied, status, f"{ws.title}!R{row}", dedupe_key))
    return transactions, reviews


VNEDU_RULE_ALIASES = (
    ("khong co phu hieu", "khong phu hieu"),
    ("khong mang sach", "quen sach"),
    ("khong mang vo", "quen sach"),
    ("chua lam bai tap", "chua lam bai tap day du"),
    ("chua thuoc bai", "khong hoc bai"),
    ("tre sang", "di hoc tre"),
    ("nghi hoc khong phep", "nghi hoc khong phep"),
)


def rule_for_vnedu(content: str, criteria_rules=None):
    """Map concise VnEdu labels to the teacher's fuller criterion wording."""
    normalized = fold(content)
    for source_label, criterion_label in VNEDU_RULE_ALIASES:
        if source_label not in normalized:
            continue
        for code, points, phrases in criteria_rules or []:
            if code.startswith("TC_TRU_") and any(criterion_label in fold(phrase) for phrase in phrases):
                return code, points
    return rule_for(content, "TRU", criteria_rules)


def extract_vnedu_violation_transactions(path: Path, students: list[Student], profile: ClassProfile, criteria_rules=None):
    """Read the VnEdu 'hs_chi_tiet' layout, including continuation rows without a name."""
    wb = load_workbook(path, data_only=True, read_only=True)
    transactions: list[Transaction] = []
    reviews: list[ReviewItem] = []
    try:
        for ws in wb.worksheets:
            header = find_header_row(ws, ("Họ và tên", "Lớp", "Hình thức", "Ngày"))
            if not header:
                continue
            header_row, columns = header
            name_col = columns[fold("Họ và tên")]
            class_col = columns[fold("Lớp")]
            form_col = columns[fold("Hình thức")]
            date_col = columns[fold("Ngày")]
            note_col = columns.get(fold("Ghi chú"))
            inherited_name = ""
            inherited_class = ""
            for row in range(header_row + 1, ws.max_row + 1):
                stated_name = compact_spaces(ws.cell(row, name_col).value)
                stated_class = normalize_class(ws.cell(row, class_col).value)
                if stated_name:
                    inherited_name = stated_name
                if stated_class:
                    inherited_class = stated_class
                content = compact_spaces(ws.cell(row, form_col).value)
                if not content or not inherited_name or inherited_class != profile.class_name:
                    continue
                # Permitted absence is recorded by VnEdu but is not a conduct deduction.
                if "nghi hoc co phep" in fold(content):
                    continue
                event_date = parse_date(ws.cell(row, date_col).value) or profile.period
                note = compact_spaces(ws.cell(row, note_col).value) if note_col else ""
                location = f"{ws.title}!R{row}"
                student, match_type, candidates = match_student(inherited_name, students)
                if not student:
                    reviews.append(ReviewItem(
                        make_id("RV", path.name, ws.title, row), path.name, location,
                        inherited_name, inherited_class, content,
                        f"Tên học sinh {match_type}", ", ".join(x.name for x in candidates),
                    ))
                    continue
                rule_code, points = rule_for_vnedu(content, criteria_rules)
                kind = "TRU"
                # Most VnEdu detailed reports are violation reports. If a school also
                # records a positive activity in this same layout, only award points
                # when it directly matches one of the saved positive criteria.
                if points is None:
                    bonus_code, bonus_points = rule_for(content, "CONG", criteria_rules)
                    if bonus_points is not None:
                        rule_code, points, kind = bonus_code, bonus_points, "CONG"
                if points is None:
                    reviews.append(ReviewItem(
                        make_id("RV", path.name, ws.title, row, "RULE"), path.name, location,
                        inherited_name, inherited_class, content,
                        "Chưa có quy tắc điểm trừ rõ ràng", student.name,
                    ))
                    status, applied = "CHO_GVCN", 0.0
                else:
                    status, applied = "DA_XAC_NHAN", points
                evidence = location if not note else f"{location}; ghi chú: {note}"
                dedupe_key = make_id("DK", student.student_id, event_date, fold(content))
                transactions.append(Transaction(
                    make_id("TX", path.name, ws.title, row), student.student_id, student.name,
                    profile.class_name, event_date, path.name, location, content, fold(content),
                    kind, rule_code, points, applied, status, evidence, dedupe_key,
                    "Đọc từ báo cáo chi tiết VnEdu",
                ))
    finally:
        wb.close()
    return transactions, reviews


def extract_vnedu_xls_transactions(path: Path, students: list[Student], profile: ClassProfile, criteria_rules=None):
    """Read a legacy VnEdu .xls file directly, without needing Microsoft Excel."""
    if xlrd is None:
        return [], [ReviewItem(
            make_id("RV", path.name, "XLRD"), path.name, "Toàn bộ tệp", "", "", "",
            "Thiếu thư viện đọc Excel .xls; hãy chạy CAI_DAT_VA_CHAY.cmd một lần",
        )]
    book = xlrd.open_workbook(path, ignore_workbook_corruption=True)
    transactions: list[Transaction] = []
    reviews: list[ReviewItem] = []
    for ws in book.sheets():
        header = find_xls_header_row(ws, ("Họ và tên", "Lớp", "Hình thức", "Ngày"))
        if not header:
            continue
        header_row, columns = header
        name_col = columns[fold("Họ và tên")]
        class_col = columns[fold("Lớp")]
        form_col = columns[fold("Hình thức")]
        date_col = columns[fold("Ngày")]
        note_col = columns.get(fold("Ghi chú"))
        inherited_name = ""
        inherited_class = ""
        for row in range(header_row + 1, ws.nrows):
            stated_name = compact_spaces(ws.cell_value(row, name_col))
            stated_class = normalize_class(ws.cell_value(row, class_col))
            if stated_name:
                inherited_name = stated_name
            if stated_class:
                inherited_class = stated_class
            content = compact_spaces(ws.cell_value(row, form_col))
            if not content or not inherited_name or inherited_class != profile.class_name:
                continue
            if "nghi hoc co phep" in fold(content):
                continue
            event_date = parse_xls_date(book, ws, row, date_col) or profile.period
            note = compact_spaces(ws.cell_value(row, note_col)) if note_col is not None else ""
            location = f"{ws.name}!R{row + 1}"
            student, match_type, candidates = match_student(inherited_name, students)
            if not student:
                reviews.append(ReviewItem(
                    make_id("RV", path.name, ws.name, row), path.name, location,
                    inherited_name, inherited_class, content,
                    f"Tên học sinh {match_type}", ", ".join(x.name for x in candidates),
                ))
                continue
            rule_code, points = rule_for_vnedu(content, criteria_rules)
            kind = "TRU"
            if points is None:
                bonus_code, bonus_points = rule_for(content, "CONG", criteria_rules)
                if bonus_points is not None:
                    rule_code, points, kind = bonus_code, bonus_points, "CONG"
            if points is None:
                reviews.append(ReviewItem(
                    make_id("RV", path.name, ws.name, row, "RULE"), path.name, location,
                    inherited_name, inherited_class, content,
                    "Chưa có quy tắc điểm trừ rõ ràng", student.name,
                ))
                status, applied = "CHO_GVCN", 0.0
            else:
                status, applied = "DA_XAC_NHAN", points
            evidence = location if not note else f"{location}; ghi chú: {note}"
            dedupe_key = make_id("DK", student.student_id, event_date, fold(content))
            transactions.append(Transaction(
                make_id("TX", path.name, ws.name, row), student.student_id, student.name,
                profile.class_name, event_date, path.name, location, content, fold(content),
                kind, rule_code, points, applied, status, evidence, dedupe_key,
                "Đọc trực tiếp từ báo cáo VnEdu .xls",
            ))
    return transactions, reviews


def parse_proposed_points(value: str) -> float | None:
    text = compact_spaces(value).replace(",", ".")
    match = re.fullmatch(r"\+?\s*(\d+(?:\.\d+)?)\s*(?:điểm|đ)?", text, flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def iter_docx_records(path: Path, target_class: str):
    doc = Document(path)
    for table_idx, table in enumerate(doc.tables, 1):
        for row_idx, row in enumerate(table.rows, 1):
            cells = [compact_spaces(c.text) for c in row.cells]
            line = " | ".join(cells)
            class_indexes = [i for i, c in enumerate(cells) if normalize_class(c) == target_class]
            if not class_indexes:
                continue
            ci = class_indexes[0]
            raw_name = cells[ci - 1] if ci >= 1 else ""
            trailing = [c for c in cells[ci + 1 :] if c]
            proposed_points = None
            point_index = None
            for index in range(len(trailing) - 1, -1, -1):
                proposed_points = parse_proposed_points(trailing[index])
                if proposed_points is not None:
                    point_index = index
                    break
            content_cells = trailing if point_index is None else trailing[:point_index]
            content = " | ".join(content_cells)
            yield table_idx, row_idx, raw_name, target_class, content or line, proposed_points


def convert_legacy_doc(path: Path, temp_dir: Path) -> tuple[Path | None, str]:
    if str(os.environ.get("V1_SKIP_LEGACY_DOC", "")).strip() == "1":
        return None, "Đã bỏ qua chuyển đổi .doc trong chế độ kiểm thử"
    script = Path(__file__).with_name("convert_legacy_doc.ps1")
    copied_doc = temp_dir / path.name
    converted_docx = temp_dir / f"{path.stem}.docx"
    shutil.copy2(path, copied_doc)
    command = [
        "powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
        "-File", str(script), "-InputFile", str(copied_doc), "-OutputFile", str(converted_docx),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=45, creationflags=creationflags)
    except subprocess.TimeoutExpired:
        return None, "Microsoft Word chuyển đổi quá thời gian 45 giây"
    if result.returncode != 0 or not converted_docx.exists():
        detail = compact_spaces(result.stderr or result.stdout)
        return None, f"Không chuyển được .doc: {detail or 'không có thông tin lỗi'}"
    return converted_docx, ""


def convert_legacy_xls(path: Path, temp_dir: Path) -> tuple[Path | None, str]:
    """Convert only a temporary copy, leaving the original VnEdu .xls untouched."""
    if str(os.environ.get("V1_SKIP_LEGACY_XLS", "")).strip() == "1":
        return None, "Đã bỏ qua chuyển đổi .xls trong chế độ kiểm thử"
    script = Path(__file__).with_name("convert_legacy_xls.ps1")
    copied_xls = temp_dir / path.name
    converted_xlsx = temp_dir / f"{path.stem}.xlsx"
    shutil.copy2(path, copied_xls)
    command = [
        "powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
        "-File", str(script), "-InputFile", str(copied_xls), "-OutputFile", str(converted_xlsx),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, creationflags=creationflags)
    except subprocess.TimeoutExpired:
        return None, "Microsoft Excel chuyển đổi quá thời gian 60 giây"
    if result.returncode != 0 or not converted_xlsx.exists():
        detail = compact_spaces(result.stderr or result.stdout)
        return None, f"Không chuyển được .xls: {detail or 'không có thông tin lỗi'}"
    return converted_xlsx, ""


def extract_activity_transactions(paths: Iterable[Path], students: list[Student], profile: ClassProfile, criteria_rules=None):
    transactions: list[Transaction] = []
    reviews: list[ReviewItem] = []
    with tempfile.TemporaryDirectory(prefix="hanh_kiem_word_") as temp_name:
        temp_dir = Path(temp_name)
        for path in paths:
            read_path = path
            if path.suffix.lower() == ".doc":
                read_path, error = convert_legacy_doc(path, temp_dir)
                if not read_path:
                    reviews.append(ReviewItem(make_id("RV", path.name, "LEGACY"), path.name, "Toàn bộ tệp", "", "", "", error))
                    continue
            try:
                records = list(iter_docx_records(read_path, profile.class_name))
            except Exception as exc:
                reviews.append(ReviewItem(make_id("RV", path.name, "READ"), path.name, "Toàn bộ tệp", "", "", "", f"Không đọc được Word: {exc}"))
                continue
            for table_idx, row_idx, raw_name, class_name, content, proposed_points in records:
                student, match_type, candidates = match_student(raw_name, students)
                location = f"Bảng {table_idx}, dòng {row_idx}"
                if not student:
                    reviews.append(ReviewItem(make_id("RV", path.name, location), path.name, location, raw_name, class_name, content, f"Tên học sinh {match_type}", ", ".join(x.name for x in candidates)))
                    continue
                rule_code, rule_points = rule_for(f"{path.stem} {content}", "CONG", criteria_rules)
                points = proposed_points if proposed_points is not None else rule_points
                if points is None:
                    reviews.append(ReviewItem(make_id("RV", path.name, location, "RULE"), path.name, location, raw_name, class_name, content, "Chưa có điểm đề nghị hoặc quy tắc điểm cộng rõ ràng", student.name))
                    continue
                event_date = parse_date(content) or profile.period
                code = rule_code or "CONG_DE_NGHI_BO_PHAN"
                dedupe_key = make_id("DK", student.student_id, event_date, fold(content))
                transactions.append(Transaction(make_id("TX", path.name, location), student.student_id, student.name, class_name, event_date, path.name, location, content, fold(content), "CONG", code, points, points, "DA_XAC_NHAN", location, dedupe_key, "Dùng điểm cộng đề nghị ghi trực tiếp trong tệp Word" if proposed_points is not None else ""))
    return transactions, reviews


def violation_category(tx: Transaction) -> str:
    """Return one stable category even when two sources use different rule codes."""
    content = tx.normalized_content or fold(tx.raw_content)
    categories = (
        ("TRU_DI_TRE", ("tre sang", "di hoc tre", "di tre", "tre hoc")),
        ("TRU_PHU_HIEU", ("phu hieu", "phu heu", "dong phuc")),
        ("TRU_DIEN_THOAI", ("dien thoai", "dtdd", "dtd d", "dtdđ")),
        ("TRU_HOC_TAP", ("khong hoc bai", "chua lam bai", "khong lam bai", "khong nop bai", "khong mang sach", "khong mang vo")),
        ("TRU_TRANG_DIEM", ("trang diem", "mang son", "son moi")),
    )
    for category, phrases in categories:
        if any(phrase in content for phrase in phrases):
            return category
    return tx.rule_code or content


def transaction_month(tx: Transaction) -> str:
    match = re.match(r"(\d{4}-\d{2})", tx.event_date)
    return match.group(1) if match else ""


def content_has_specific_date(content: object) -> bool:
    text = compact_spaces(content)
    return bool(re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\b\d{4}-\d{2}-\d{2}\b", text))


def deduplicate(transactions: list[Transaction]):
    kept = []
    duplicate_count = 0
    exact_seen: dict[str, Transaction] = {}
    semantic_seen: dict[tuple[str, str, str], Transaction] = {}
    specific_dated_categories = {
        (tx.student_id, transaction_month(tx), violation_category(tx))
        for tx in transactions
        if tx.kind == "TRU" and content_has_specific_date(tx.raw_content)
    }
    for tx in transactions:
        month_key = transaction_month(tx)
        category = violation_category(tx)
        if (
            tx.kind == "TRU"
            and not content_has_specific_date(tx.raw_content)
            and (tx.student_id, month_key, category) in specific_dated_categories
        ):
            duplicate_count += 1
            tx.status = "LOAI_BO_TRUNG_KHONG_NGAY"
            tx.applied_points = 0.0
            tx.note = "Không áp dụng hoặc hiển thị: cùng loại lỗi đã có ngày cụ thể trong tháng"
            kept.append(tx)
            continue
        exact = exact_seen.get(tx.dedupe_key)
        semantic_key = (tx.student_id, tx.event_date, category)
        semantic = semantic_seen.get(semantic_key) if category else None
        fuzzy = None
        if tx.source_file.startswith("Tổng hợp vi phạm"):
            date_match = re.match(r"\d{4}-(\d{2})-(\d{2})", tx.event_date)
            date_tokens = ""
            if date_match:
                month = str(int(date_match.group(1)))
                day = str(int(date_match.group(2)))
                date_tokens = f"{day} {month}"
            for earlier in kept:
                if earlier.student_id != tx.student_id or earlier.kind != "TRU":
                    continue
                same_content = tx.normalized_content and tx.normalized_content in earlier.normalized_content
                same_date_in_combined_note = date_tokens and date_tokens in earlier.normalized_content
                if same_content and same_date_in_combined_note:
                    fuzzy = earlier
                    break
        prior = exact or semantic or fuzzy
        if prior:
            duplicate_count += 1
            tx.status = "TRUNG_NGUON"
            tx.applied_points = 0.0
            tx.note = f"Không áp dụng; có thể trùng {prior.transaction_id} từ {prior.source_file}"
        else:
            exact_seen[tx.dedupe_key] = tx
            if category:
                semantic_seen[semantic_key] = tx
        kept.append(tx)
    return kept, duplicate_count


def cap_bonuses(transactions: list[Transaction], bonus_cap: float = DEFAULT_BONUS_CAP):
    used = defaultdict(float)
    for tx in transactions:
        if tx.kind != "CONG" or tx.status not in {"DA_XAC_NHAN", "VUOT_TRAN"}:
            continue
        available = max(0.0, bonus_cap - used[tx.student_id])
        if tx.applied_points > available:
            tx.applied_points = available
            tx.status = "VUOT_TRAN"
            tx.note = f"Điểm cộng được giới hạn để tổng tháng không vượt +{bonus_cap:g}"
        used[tx.student_id] += tx.applied_points


def rating(score: float) -> str:
    if score >= 80:
        return "TỐT"
    if score >= 65:
        return "KHÁ"
    if score >= 50:
        return "ĐẠT"
    return "CHƯA ĐẠT"


def ensure_sheet(wb, title: str):
    if title in wb.sheetnames:
        del wb[title]
    return wb.create_sheet(title)


def style_table(ws, max_col: int):
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1][:max_col]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True, name="Arial", size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def export_workbook(template_path: Path, output_path: Path, students: list[Student], profile: ClassProfile, transactions: list[Transaction], reviews: list[ReviewItem], source_files: list[str], criteria_report=None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, output_path)
    wb = load_workbook(output_path)
    ws = wb[profile.sheet_name]
    wb.active = wb.sheetnames.index(profile.sheet_name)
    by_student = defaultdict(list)
    for tx in transactions:
        by_student[tx.student_id].append(tx)
    for row, student in enumerate(students, 2):
        txs = by_student[student.student_id]
        positives = [x for x in txs if x.kind == "CONG" and x.applied_points > 0]
        negatives = [x for x in txs if x.kind == "TRU" and x.applied_points > 0]
        improvement_items = [
            x for x in txs
            if x.kind == "TRU" and (x.applied_points > 0 or x.status in {"GHI_NHAN", "CHO_GVCN"})
        ]
        bonus = sum(x.applied_points for x in positives)
        deduction = sum(x.applied_points for x in negatives)
        total = profile.base_score + bonus - deduction
        ws.cell(row, 1).value = student.stt
        ws.cell(row, 2).value = student.name
        ws.cell(row, 3).value = student.class_name
        fixed_bonus_labels = [
            ("Thực hiện tốt học tập", "CONG_025_HOC_TAP"),
            ("Thực hiện tốt chuyên cần", "CONG_025_CHUYEN_CAN"),
            ("Thực hiện tốt tác phong, đồng phục", "CONG_025_TAC_PHONG"),
        ]
        fixed_codes = {code for _, code in fixed_bonus_labels}
        fixed_totals = defaultdict(float)
        positive_totals = defaultdict(float)
        for item in positives:
            if item.rule_code in fixed_codes:
                fixed_totals[item.rule_code] += item.applied_points
            else:
                positive_totals[item.raw_content] += item.applied_points
        positive_parts = [
            f"- {label}: +{display_points_vn(fixed_totals[code])}đ"
            for label, code in fixed_bonus_labels
        ]
        for label, points in positive_totals.items():
            prefix = "*" if "cán" in label.lower() or "nhiệm vụ" in label.lower() else "-"
            positive_parts.append(f"{prefix} {label} (+{display_number(points)})")
        ws.cell(row, 4).value = "\n".join(positive_parts)
        ws.cell(row, 5).value = display_number(bonus)
        ws.cell(row, 6).value = "\n".join(format_improvement_line(x.raw_content, x.applied_points) for x in improvement_items)
        ws.cell(row, 7).value = display_number(deduction)
        ws.cell(row, 8).value = f"={display_number(profile.base_score)}+E{row}-G{row}"
        ws.cell(row, 9).value = f'=IF(H{row}>=80,"TỐT",IF(H{row}>=65,"KHÁ",IF(H{row}>=50,"ĐẠT","CHƯA ĐẠT")))'
        pending = sum(1 for x in txs if x.status == "CHO_GVCN")
        ws.cell(row, 10).value = f"Có {pending} giao dịch chờ xác nhận" if pending else ""
        ws.cell(row, 6).alignment = Alignment(vertical="top", wrap_text=True)
        line_count = max(str(ws.cell(row, 4).value or "").count("\n") + 1, str(ws.cell(row, 6).value or "").count("\n") + 1)
        text_length = max(len(str(ws.cell(row, 4).value or "")), len(str(ws.cell(row, 6).value or "")))
        ws.row_dimensions[row].height = min(150, max(30, 18 * line_count + 12 * (text_length // 90)))
    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = False
    ws.sheet_view.topLeftCell = "A1"
    for selection in ws.sheet_view.selection:
        selection.activeCell = "A1"
        selection.sqref = "A1"
    for idx in range(1, ws.max_row + 1):
        ws.row_dimensions[idx].hidden = False
    for dimension in ws.column_dimensions.values():
        dimension.hidden = False

    s_students = ensure_sheet(wb, "DANH_SACH_HS")
    s_students.append(["Mã HS", "STT", "Họ tên chuẩn", "Lớp", "Bí danh tự động"])
    for student in students:
        s_students.append([student.student_id, student.stt, student.name, student.class_name, "; ".join(student.aliases)])
    style_table(s_students, 5)
    for col, width in {"A": 14, "B": 8, "C": 30, "D": 10, "E": 40}.items():
        s_students.column_dimensions[col].width = width

    s_tx = ensure_sheet(wb, "GIAO_DICH_DIEM")
    tx_headers = ["Mã giao dịch", "Mã HS", "Họ tên", "Lớp", "Ngày", "Nguồn", "Vị trí nguồn", "Nội dung gốc", "Nội dung chuẩn hóa", "Loại", "Mã quy tắc", "Điểm đề nghị", "Điểm áp dụng", "Trạng thái", "Minh chứng", "Mã chống trùng", "Ghi chú"]
    s_tx.append(tx_headers)
    for tx in transactions:
        s_tx.append([tx.transaction_id, tx.student_id, tx.student_name, tx.class_name, tx.event_date, tx.source_file, tx.source_location, tx.raw_content, tx.normalized_content, tx.kind, tx.rule_code, tx.proposed_points, tx.applied_points, tx.status, tx.evidence, tx.dedupe_key, tx.note])
    style_table(s_tx, len(tx_headers))
    for col, width in {"A":18,"B":14,"C":28,"D":10,"E":14,"F":38,"G":24,"H":48,"I":42,"J":10,"K":24,"L":14,"M":14,"N":16,"O":24,"P":20,"Q":48}.items():
        s_tx.column_dimensions[col].width = width

    s_review = ensure_sheet(wb, "CAN_GVCN_XAC_NHAN")
    review_headers = ["Mã", "Nguồn", "Vị trí", "Tên gốc", "Lớp", "Nội dung", "Lý do", "Gợi ý học sinh", "Gợi ý quy tắc", "GVCN quyết định"]
    s_review.append(review_headers)
    for item in reviews:
        s_review.append([item.review_id, item.source_file, item.source_location, item.raw_name, item.class_name, item.raw_content, item.reason, item.suggested_student, item.suggested_rule, ""])
    style_table(s_review, len(review_headers))
    for col, width in {"A":18,"B":38,"C":24,"D":24,"E":10,"F":48,"G":38,"H":30,"I":24,"J":30}.items():
        s_review.column_dimensions[col].width = width

    s_rules = ensure_sheet(wb, "QUY_TAC")
    s_rules.append(["Mã quy tắc", "Loại", "Điểm", "Từ khóa nhận diện"])
    for code, points, phrases in DEDUCTION_RULES:
        s_rules.append([code, "TRỪ", points, "; ".join(phrases)])
    for code, points, phrases in ACTIVITY_RULES:
        s_rules.append([code, "CỘNG", points, "; ".join(phrases)])
    for code, kind, points, content in criteria_report or []:
        s_rules.append([code, kind, points, content])
    s_rules.append(["CONG_025_HOC_TAP", "CỘNG", 0.25, "Mỗi tuần thực hiện tốt học tập"])
    s_rules.append(["CONG_025_CHUYEN_CAN", "CỘNG", 0.25, "Mỗi tuần thực hiện tốt chuyên cần"])
    s_rules.append(["CONG_025_TAC_PHONG", "CỘNG", 0.25, "Mỗi tuần thực hiện tốt tác phong, đồng phục"])
    s_rules.append(["TRẦN_CỘNG", "GIỚI HẠN", profile.bonus_cap, "Tổng điểm cộng tối đa mỗi HS mỗi tháng"])
    style_table(s_rules, 4)
    for col, width in {"A":28,"B":14,"C":12,"D":70}.items():
        s_rules.column_dimensions[col].width = width

    s_log = ensure_sheet(wb, "NHAT_KY_TONG_HOP")
    s_log.append(["Thời điểm", "Lớp", "Điểm gốc", "Trần điểm cộng", "Số học sinh", "Số giao dịch", "Số cần xác nhận", "Các tệp nguồn"])
    s_log.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), profile.class_name, profile.base_score, profile.bonus_cap, len(students), len(transactions), len(reviews), "\n".join(source_files)])
    style_table(s_log, 8)
    for col, width in {"A":22,"B":10,"C":12,"D":16,"E":14,"F":14,"G":18,"H":80}.items():
        s_log.column_dimensions[col].width = width

    wb.save(output_path)


def run_pipeline(source_dir: str | Path, output_dir: str | Path) -> RunResult:
    selected_source_path = Path(source_dir).resolve()
    selected_file = selected_source_path if selected_source_path.is_file() else None
    selected_source_dir = selected_source_path.parent if selected_file else selected_source_path
    source_dir = locate_source_folder(selected_source_path)
    output_dir = Path(output_dir).resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Khong tim thay thu muc nguon: {source_dir}")
    source_files = [selected_file.name] if selected_file else sorted([p.name for p in source_dir.iterdir() if p.is_file()])
    template_info = find_template_file(source_dir)
    monthly = find_weekly_file(source_dir)
    violations = [selected_file] if selected_file and selected_file.suffix.lower() in {".xlsx", ".xls"} else find_violation_files(source_dir)
    if selected_file and selected_file not in find_violation_files(source_dir):
        raise ValueError("File được chọn không phải báo cáo vi phạm hoặc báo cáo chi tiết VnEdu")
    vnedu_files = [
        path for path in violations
        if (path.suffix.lower() == ".xlsx" and is_vnedu_violation_workbook(path))
        or (path.suffix.lower() == ".xls" and is_vnedu_violation_xls(path))
    ]
    project_root = Path(__file__).resolve().parents[1]
    vnedu_class, vnedu_period = "", ""
    if len(vnedu_files) == 1:
        if vnedu_files[0].suffix.lower() == ".xls":
            vnedu_class, vnedu_period = vnedu_xls_class_and_period(vnedu_files[0])
        else:
            vnedu_class, vnedu_period = vnedu_class_and_period(vnedu_files[0])
    if not template_info and vnedu_class:
        template_info = saved_class_template(project_root, vnedu_class)
    template = template_info[0] if template_info else None
    template_sheet = template_info[1] if template_info else ""
    if not template or not violations:
        missing = []
        if not template:
            if vnedu_class:
                missing.append(f"file mẫu đã thiết lập cho lớp {vnedu_class}")
            else:
                missing.append("file mẫu hạnh kiểm/rèn luyện")
        if not violations:
            missing.append("file vi phạm hoặc báo cáo VnEdu")
        raise FileNotFoundError(
            f"Thư mục nguồn đang chọn: {selected_source_dir}\n"
            f"Không tìm thấy: {', '.join(missing)}.\n"
            "Lần đầu cho mỗi lớp, hãy bấm THIẾT LẬP MẪU LỚP để lưu file mẫu. "
            "Sau đó, mỗi tháng có thể chọn trực tiếp file VnEdu."
        )
    students, profile = load_students(template, template_sheet)
    if vnedu_class and profile.class_name != vnedu_class:
        raise ValueError(f"File mẫu thuộc lớp {profile.class_name}, nhưng báo cáo VnEdu thuộc lớp {vnedu_class}")
    if vnedu_period:
        profile.period = vnedu_period
    criteria_rules, criteria_report = load_criteria_rules(project_root)
    transactions: list[Transaction] = []
    reviews: list[ReviewItem] = []
    if monthly and not selected_file:
        tx, rv = extract_weekly_transactions(monthly, students, profile, criteria_rules)
        transactions.extend(tx); reviews.extend(rv)
    with tempfile.TemporaryDirectory(prefix="hanh_kiem_xls_") as temp_name:
        temp_dir = Path(temp_name)
        for violation_path in violations:
            read_path = violation_path
            if violation_path.suffix.lower() == ".xls" and is_vnedu_violation_xls(violation_path):
                tx, rv = extract_vnedu_xls_transactions(violation_path, students, profile, criteria_rules)
                transactions.extend(tx); reviews.extend(rv)
                continue
            if violation_path.suffix.lower() == ".xls":
                read_path, error = convert_legacy_xls(violation_path, temp_dir)
                if not read_path:
                    reviews.append(ReviewItem(make_id("RV", violation_path.name, "LEGACY"), violation_path.name, "Toàn bộ tệp", "", "", "", error))
                    continue
            if is_vnedu_violation_workbook(read_path):
                tx, rv = extract_vnedu_violation_transactions(read_path, students, profile, criteria_rules)
            else:
                tx, rv = extract_violation_transactions(read_path, students, profile, criteria_rules)
            transactions.extend(tx); reviews.extend(rv)
    word_files = [p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() in {".doc", ".docx"}]
    tx, rv = extract_activity_transactions(word_files, students, profile, criteria_rules)
    transactions.extend(tx); reviews.extend(rv)
    transactions, duplicate_count = deduplicate(transactions)
    cap_bonuses(transactions, profile.bonus_cap)
    output_name = f"KET_QUA_HANH_KIEM_{profile.class_name}_{profile.period}.xlsx"
    output_path = output_dir / output_name
    export_workbook(template, output_path, students, profile, transactions, reviews, source_files, criteria_report)
    result = RunResult(str(output_path), len(students), len(transactions), len(reviews), duplicate_count, source_files)
    (output_dir / "ket_qua_lan_chay.json").write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return result
