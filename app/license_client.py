"""
license_client.py — Module quản lý quyền sử dụng từ xa (Supabase)

Nguyên tắc:
- Chỉ dùng SUPABASE_URL và SUPABASE_ANON_KEY (khóa công khai).
- KHÔNG gửi dữ liệu học sinh, file Word/Excel, điểm số lên server.
- KHÔNG dùng MAC address, Wi-Fi, GPS, dữ liệu trình duyệt.
- Mã thiết bị tạo từ Windows MachineGuid (ẩn danh, cố định theo máy).
- Cache license lưu tại %APPDATA% — chung cho mọi bản copy của .exe.
- Cho phép offline tối đa 14 ngày kể từ lần kiểm tra hợp lệ gần nhất.
- Khi quyền bị thu hồi, hiện thông báo tiếng Việt rõ ràng.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Trạng thái thiết bị
STATUS_CHO_DUYET = "CHO_DUYET"
STATUS_DANG_HOAT_DONG = "DANG_HOAT_DONG"
STATUS_DA_THU_HOI = "DA_THU_HOI"
STATUS_TAM_NGUNG = "TAM_NGUNG"

# Thời gian offline tối đa (14 ngày)
MAX_OFFLINE_DAYS = 14

# Tên file lưu cache license local
LICENSE_CACHE_FILE = ".license_cache.json"

# App version — cập nhật mỗi khi ra bản mới
APP_VERSION = "2.19"

# ---------------------------------------------------------------------------
# Supabase Config — Nhúng sẵn để không bị bypass khi thiếu .env
# Đây là anon (public) key, an toàn để nhúng trong client.
# ---------------------------------------------------------------------------
_EMBEDDED_SUPABASE_URL = "https://ezkihonyfnajpdidvwsj.supabase.co"
_EMBEDDED_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6a2lob255Zm5hanBkaWR2d3NqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE2NDI2MzgsImV4cCI6MjEwNzIxODYzOH0."
    "-GIu2SNF48mRg-oboRth1hsEckYkZxSGcIiZ4kx2Z7k"
)


def _get_config_dir() -> Path:
    """
    Thư mục lưu cache license — luôn nằm trong %APPDATA%.
    Mọi bản copy của .exe trên cùng máy đều dùng chung thư mục này.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        config_dir = Path(appdata) / "TuyenBui" / "HeThongHanhKiem"
    else:
        # Fallback cho môi trường dev hoặc non-Windows
        config_dir = Path.home() / ".tuyenbui" / "hethonghanhkiem"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _cache_path() -> Path:
    return _get_config_dir() / LICENSE_CACHE_FILE


# ---------------------------------------------------------------------------
# Supabase Config — Đọc từ biến môi trường, file .env, hoặc giá trị nhúng sẵn
# ---------------------------------------------------------------------------

def _load_env_file() -> dict:
    """Đọc file .env nếu có."""
    env_data = {}
    candidates = []
    # Nếu đóng gói exe, tìm .env bên cạnh exe hoặc trong _MEIPASS
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys.executable).parent / ".env")
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(Path(meipass) / ".env")
    candidates.extend([
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent / ".env",
    ])
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            env_data[key] = value
            except Exception:
                pass
            break
    return env_data


def get_supabase_config() -> Tuple[str, str]:
    """
    Lấy SUPABASE_URL và SUPABASE_ANON_KEY.
    Ưu tiên: biến môi trường > file .env > giá trị nhúng sẵn trong mã.
    Luôn trả về giá trị hợp lệ (không bao giờ trả về None).
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        env_data = _load_env_file()
        url = url or env_data.get("SUPABASE_URL")
        key = key or env_data.get("SUPABASE_ANON_KEY")

    # Fallback: dùng giá trị nhúng sẵn (anon key là khóa công khai, an toàn)
    if not url:
        url = _EMBEDDED_SUPABASE_URL
    if not key:
        key = _EMBEDDED_SUPABASE_ANON_KEY

    url = url.rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[:-len("/rest/v1")]
    return url, key


# ---------------------------------------------------------------------------
# HTTP Client — Dùng urllib chuẩn, không cần thêm thư viện
# ---------------------------------------------------------------------------

import urllib.request
import urllib.error
import urllib.parse
import ssl


def _make_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    body: Optional[dict] = None,
    timeout: int = 10,
) -> Tuple[int, Optional[dict]]:
    """Gửi HTTP request đến Supabase REST API. Trả về (status_code, json_data)."""
    if headers is None:
        headers = {}

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    # Tạo SSL context cho phép kết nối HTTPS
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp_data = resp.read().decode("utf-8")
            try:
                json_resp = json.loads(resp_data) if resp_data.strip() else None
            except json.JSONDecodeError:
                json_resp = None
            return resp.status, json_resp
    except urllib.error.HTTPError as e:
        resp_data = e.read().decode("utf-8") if e.fp else ""
        try:
            json_resp = json.loads(resp_data) if resp_data.strip() else None
        except json.JSONDecodeError:
            json_resp = {"error": resp_data}
        return e.code, json_resp
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, None  # Không có kết nối


def _supabase_headers(anon_key: str) -> dict:
    """Headers chuẩn cho Supabase REST API."""
    return {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


# ---------------------------------------------------------------------------
# License Cache — Lưu local để hoạt động offline
# ---------------------------------------------------------------------------

class LicenseCache:
    """Quản lý cache license trên máy local."""

    def __init__(self):
        self.device_uuid: Optional[str] = None
        self.user_name: Optional[str] = None
        self.organization: Optional[str] = None
        self.status: Optional[str] = None
        self.last_valid_check: Optional[str] = None  # ISO format
        self.registered: bool = False

    def save(self):
        """Lưu cache ra file."""
        data = {
            "device_uuid": self.device_uuid,
            "user_name": self.user_name,
            "organization": self.organization,
            "status": self.status,
            "last_valid_check": self.last_valid_check,
            "registered": self.registered,
            "cache_version": 1,
        }
        try:
            with open(_cache_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def load(cls) -> "LicenseCache":
        """Đọc cache từ file."""
        cache = cls()
        try:
            if _cache_path().is_file():
                with open(_cache_path(), "r", encoding="utf-8") as f:
                    data = json.load(f)
                cache.device_uuid = data.get("device_uuid")
                cache.user_name = data.get("user_name")
                cache.organization = data.get("organization")
                cache.status = data.get("status")
                cache.last_valid_check = data.get("last_valid_check")
                cache.registered = data.get("registered", False)
        except Exception:
            pass
        return cache

    def is_offline_valid(self) -> bool:
        """Kiểm tra còn trong thời hạn offline không (14 ngày)."""
        if not self.last_valid_check:
            return False
        try:
            last_check = datetime.fromisoformat(self.last_valid_check)
            return datetime.now() - last_check < timedelta(days=MAX_OFFLINE_DAYS)
        except (ValueError, TypeError):
            return False

    def days_since_last_check(self) -> Optional[int]:
        """Số ngày kể từ lần kiểm tra gần nhất."""
        if not self.last_valid_check:
            return None
        try:
            last_check = datetime.fromisoformat(self.last_valid_check)
            return (datetime.now() - last_check).days
        except (ValueError, TypeError):
            return None

    def needs_online_check(self) -> bool:
        """
        Luôn kiểm tra online mỗi khi mở app.
        Chỉ dùng cache khi hoàn toàn mất kết nối Internet.
        """
        return True


# ---------------------------------------------------------------------------
# License Client — API chính
# ---------------------------------------------------------------------------

class LicenseCheckResult:
    """Kết quả kiểm tra license."""

    def __init__(self):
        self.allowed: bool = False
        self.status: Optional[str] = None
        self.message: str = ""
        self.need_registration: bool = False
        self.is_offline: bool = False


def get_machine_name() -> str:
    """Lấy tên máy tính (hostname). Không lấy MAC address."""
    try:
        return platform.node() or "Unknown"
    except Exception:
        return "Unknown"


def _get_machine_guid() -> Optional[str]:
    """
    Đọc Windows MachineGuid từ Registry.
    Đây là GUID ẩn danh do Windows cấp cho mỗi máy tính,
    KHÔNG phải MAC address, Wi-Fi, GPS hay dữ liệu trình duyệt.
    """
    if not sys.platform.startswith("win"):
        return None
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(guid)
    except Exception:
        return None


def generate_device_uuid() -> str:
    """
    Tạo UUID cố định cho thiết bị dựa trên Windows MachineGuid.
    Cùng một máy tính luôn sinh ra cùng một UUID,
    dù file .exe được copy sang bất kỳ thư mục nào.
    Không dùng MAC address.
    """
    machine_guid = _get_machine_guid()
    if machine_guid:
        # Tạo UUID v5 (deterministic) từ MachineGuid
        # Dùng namespace cố định để đảm bảo kết quả nhất quán
        namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        return str(uuid.uuid5(namespace, machine_guid))
    else:
        # Fallback cho non-Windows: dùng hostname + platform
        fallback_id = f"{platform.node()}-{platform.machine()}-{platform.system()}"
        namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        return str(uuid.uuid5(namespace, fallback_id))


def register_device(
    user_name: str,
    organization: str,
    device_uuid: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Đăng ký thiết bị mới lên Supabase.
    
    Trả về (success, message).
    Chỉ gửi: tên người dùng, đơn vị, tên máy, UUID thiết bị, phiên bản app.
    KHÔNG gửi: dữ liệu học sinh, file Word/Excel, điểm số.
    """
    supa_url, anon_key = get_supabase_config()

    if not device_uuid:
        device_uuid = generate_device_uuid()

    machine_name = get_machine_name()
    now_iso = datetime.now().isoformat()

    # Kiểm tra thiết bị đã đăng ký chưa
    check_url = (
        f"{supa_url}/rest/v1/devices"
        f"?device_uuid=eq.{urllib.parse.quote(device_uuid)}"
        f"&select=id,status,user_name,organization"
    )
    status_code, existing = _make_request(
        check_url,
        method="GET",
        headers=_supabase_headers(anon_key),
    )

    if status_code == 200 and existing and len(existing) > 0:
        # Thiết bị đã tồn tại trên server -> Khôi phục cache local thành công
        dev = existing[0]
        cache = LicenseCache()
        cache.device_uuid = device_uuid
        cache.user_name = user_name.strip() or dev.get("user_name", "")
        cache.organization = organization.strip() or dev.get("organization", "")
        cache.status = dev.get("status", STATUS_CHO_DUYET)
        cache.last_valid_check = now_iso
        cache.registered = True
        cache.save()
        return True, device_uuid

    # Đăng ký thiết bị mới
    register_url = f"{supa_url}/rest/v1/devices"
    body = {
        "device_uuid": device_uuid,
        "machine_name": machine_name,
        "user_name": user_name.strip(),
        "organization": organization.strip() if organization else "",
        "status": STATUS_CHO_DUYET,
        "app_version": APP_VERSION,
        "created_at": now_iso,
        "last_seen_at": now_iso,
        "last_check_at": now_iso,
    }

    status_code, resp = _make_request(
        register_url,
        method="POST",
        headers=_supabase_headers(anon_key),
        body=body,
    )

    if status_code in (200, 201):
        # Ghi event đăng ký
        _log_license_event(supa_url, anon_key, device_uuid, "DANG_KY",
                           f"Đăng ký thiết bị mới: {user_name} - {machine_name}")

        # Lưu cache local
        cache = LicenseCache()
        cache.device_uuid = device_uuid
        cache.user_name = user_name
        cache.organization = organization
        cache.status = STATUS_CHO_DUYET
        cache.last_valid_check = now_iso
        cache.registered = True
        cache.save()

        return True, device_uuid

    error_msg = "Không thể đăng ký thiết bị."
    if resp and isinstance(resp, dict):
        error_msg += f" ({resp.get('message', resp.get('error', ''))})"
    return False, error_msg


def check_license(device_uuid: Optional[str] = None) -> LicenseCheckResult:
    """
    Kiểm tra quyền sử dụng.
    
    Logic:
    1. Đọc cache local
    2. Nếu chưa đăng ký → yêu cầu đăng ký
    3. Nếu có Internet → kiểm tra online
    4. Nếu không có Internet:
       - Còn trong 14 ngày → cho phép offline
       - Quá 14 ngày → yêu cầu kết nối
    """
    result = LicenseCheckResult()
    cache = LicenseCache.load()

    # Nếu chưa có cache hoặc chưa ghi nhận đăng ký
    if not cache.registered or not cache.device_uuid:
        current_uuid = device_uuid or generate_device_uuid()
        supa_url, anon_key = get_supabase_config()
        check_url = (
            f"{supa_url}/rest/v1/devices"
            f"?device_uuid=eq.{urllib.parse.quote(current_uuid)}"
            f"&select=id,device_uuid,user_name,organization,status,last_check_at"
        )
        status_code, data = _make_request(
            check_url,
            method="GET",
            headers=_supabase_headers(anon_key),
            timeout=5,
        )
        if status_code == 200 and isinstance(data, list) and len(data) > 0:
            # Thiết bị đã có trên server -> Tự động phục hồi cache
            dev = data[0]
            cache.device_uuid = current_uuid
            cache.user_name = dev.get("user_name", "")
            cache.organization = dev.get("organization", "")
            cache.status = dev.get("status", STATUS_CHO_DUYET)
            cache.last_valid_check = datetime.now().isoformat()
            cache.registered = True
            cache.save()
            device_uuid = current_uuid
        else:
            result.need_registration = True
            result.message = "Thiết bị chưa được đăng ký."
            return result

    if device_uuid is None:
        device_uuid = cache.device_uuid

    # Kiểm tra có cần check online không
    if not cache.needs_online_check():
        # Chưa đến 24h, dùng cache
        if cache.status == STATUS_DA_THU_HOI:
            result.allowed = False
            result.status = STATUS_DA_THU_HOI
            result.message = (
                "Quyền sử dụng ứng dụng này không còn hiệu lực. "
                "Vui lòng liên hệ TB."
            )
        elif cache.status == STATUS_TAM_NGUNG:
            result.allowed = False
            result.status = STATUS_TAM_NGUNG
            result.message = (
                "Quyền sử dụng ứng dụng tạm thời bị tạm ngưng. "
                "Vui lòng liên hệ TB."
            )
        elif cache.status == STATUS_DANG_HOAT_DONG:
            result.allowed = True
            result.status = STATUS_DANG_HOAT_DONG
            result.message = "Quyền sử dụng hợp lệ."
        elif cache.status == STATUS_CHO_DUYET:
            # Cho phép dùng khi chờ duyệt (thiết bị mới)
            result.allowed = True
            result.status = STATUS_CHO_DUYET
            result.message = (
                "Thiết bị đang chờ được duyệt. "
                "Bạn vẫn có thể sử dụng ứng dụng trong thời gian chờ."
            )
        else:
            result.allowed = True
            result.status = cache.status
        return result

    # Cần kiểm tra online — luôn lấy config (không bao giờ None nhờ embedded fallback)
    supa_url, anon_key = get_supabase_config()

    # Gọi API kiểm tra
    check_url = (
        f"{supa_url}/rest/v1/devices"
        f"?device_uuid=eq.{urllib.parse.quote(device_uuid)}"
        f"&select=id,device_uuid,status,last_check_at"
    )
    status_code, data = _make_request(
        check_url,
        method="GET",
        headers=_supabase_headers(anon_key),
        timeout=8,
    )

    if status_code == 0 or data is None:
        # Không có Internet
        result.is_offline = True
        if cache.is_offline_valid():
            days = cache.days_since_last_check() or 0
            remaining = MAX_OFFLINE_DAYS - days
            if cache.status in (STATUS_DANG_HOAT_DONG, STATUS_CHO_DUYET):
                result.allowed = True
                result.message = (
                    f"Đang hoạt động offline. Còn {remaining} ngày "
                    f"trước khi cần kết nối Internet để xác minh quyền sử dụng."
                )
            elif cache.status == STATUS_DA_THU_HOI:
                result.allowed = False
                result.status = STATUS_DA_THU_HOI
                result.message = (
                    "Quyền sử dụng ứng dụng này không còn hiệu lực. "
                    "Vui lòng liên hệ TB."
                )
            elif cache.status == STATUS_TAM_NGUNG:
                result.allowed = False
                result.status = STATUS_TAM_NGUNG
                result.message = (
                    "Quyền sử dụng ứng dụng tạm thời bị tạm ngưng. "
                    "Vui lòng liên hệ TB."
                )
            else:
                result.allowed = True
                result.message = f"Hoạt động offline. Còn {remaining} ngày."
        else:
            result.allowed = False
            result.message = (
                "Đã quá 14 ngày không thể xác minh quyền sử dụng.\n"
                "Vui lòng kết nối Internet để ứng dụng kiểm tra quyền sử dụng."
            )
        result.status = cache.status
        return result

    # Có kết nối — xử lý kết quả
    if status_code == 200 and isinstance(data, list) and len(data) > 0:
        device = data[0]
        server_status = device.get("status", STATUS_CHO_DUYET)
        now_iso = datetime.now().isoformat()
        status_changed = (cache.status != server_status)

        # Cập nhật cache
        cache.status = server_status
        cache.last_valid_check = now_iso
        cache.save()

        # Khi trạng thái thay đổi: ghi log sự kiện và cập nhật server ngay lập tức
        if status_changed:
            _update_device_check(supa_url, anon_key, device_uuid, now_iso)
            _log_license_event(supa_url, anon_key, device_uuid, "THAY_DOI_TRANG_THAI",
                               f"Trạng thái cập nhật: {server_status}")

        result.status = server_status

        if server_status == STATUS_DANG_HOAT_DONG:
            result.allowed = True
            result.message = "Quyền sử dụng hợp lệ."
        elif server_status == STATUS_CHO_DUYET:
            result.allowed = True
            result.message = (
                "Thiết bị đang chờ được duyệt. "
                "Bạn vẫn có thể sử dụng ứng dụng trong thời gian chờ."
            )
        elif server_status == STATUS_DA_THU_HOI:
            result.allowed = False
            result.message = (
                "Quyền sử dụng ứng dụng này không còn hiệu lực. "
                "Vui lòng liên hệ TB."
            )
        elif server_status == STATUS_TAM_NGUNG:
            result.allowed = False
            result.message = (
                "Quyền sử dụng ứng dụng tạm thời bị tạm ngưng. "
                "Vui lòng liên hệ TB."
            )
        else:
            result.allowed = True
            result.message = f"Trạng thái: {server_status}"
    elif status_code == 200 and isinstance(data, list) and len(data) == 0:
        # Thiết bị không tồn tại trên server — cần đăng ký lại
        result.need_registration = True
        result.message = "Thiết bị chưa được đăng ký trên hệ thống."
        # Xóa cache cũ
        cache.registered = False
        cache.save()
    else:
        # Lỗi server — fallback offline
        result.is_offline = True
        if cache.is_offline_valid() and cache.status in (STATUS_DANG_HOAT_DONG, STATUS_CHO_DUYET):
            result.allowed = True
            result.message = "Không thể kết nối server. Đang hoạt động offline."
        else:
            result.allowed = False
            result.message = (
                "Không thể xác minh quyền sử dụng.\n"
                "Vui lòng kiểm tra kết nối Internet và thử lại."
            )
        result.status = cache.status

    return result


def _update_device_check(supa_url: str, anon_key: str, device_uuid: str, now_iso: str):
    """Cập nhật last_seen_at và last_check_at trên server."""
    try:
        update_url = (
            f"{supa_url}/rest/v1/devices"
            f"?device_uuid=eq.{urllib.parse.quote(device_uuid)}"
        )
        _make_request(
            update_url,
            method="PATCH",
            headers=_supabase_headers(anon_key),
            body={
                "last_seen_at": now_iso,
                "last_check_at": now_iso,
                "app_version": APP_VERSION,
            },
            timeout=5,
        )
    except Exception:
        pass


def _log_license_event(
    supa_url: str,
    anon_key: str,
    device_uuid: str,
    event_type: str,
    detail: str,
    admin_email: str = "",
):
    """Ghi lịch sử sự kiện license."""
    try:
        event_url = f"{supa_url}/rest/v1/license_events"
        _make_request(
            event_url,
            method="POST",
            headers=_supabase_headers(anon_key),
            body={
                "device_uuid": device_uuid,
                "event_type": event_type,
                "detail": detail,
                "admin_email": admin_email,
                "created_at": datetime.now().isoformat(),
            },
            timeout=5,
        )
    except Exception:
        pass


def clear_license_cache():
    """Xóa cache license local (dùng khi cần đăng ký lại)."""
    try:
        if _cache_path().is_file():
            _cache_path().unlink()
    except Exception:
        pass


def check_license_quick() -> Tuple[bool, str]:
    """
    Kiểm tra nhanh quyền sử dụng trước khi thực hiện thao tác quan trọng
    (ví dụ: nhấn nút TỔNG HỢP).
    Trả về (allowed, message).
    Nếu có Internet, gửi truy vấn trực tiếp lên Supabase.
    """
    cache = LicenseCache.load()
    if not cache.registered or not cache.device_uuid:
        return False, "Thiết bị chưa được đăng ký."

    supa_url, anon_key = get_supabase_config()

    check_url = (
        f"{supa_url}/rest/v1/devices"
        f"?device_uuid=eq.{urllib.parse.quote(cache.device_uuid)}"
        f"&select=status"
    )
    status_code, data = _make_request(
        check_url, "GET", _supabase_headers(anon_key), timeout=5,
    )

    if status_code == 200 and isinstance(data, list) and len(data) > 0:
        server_status = data[0].get("status", STATUS_CHO_DUYET)
        # Cập nhật cache ngay
        cache.status = server_status
        cache.last_valid_check = datetime.now().isoformat()
        cache.save()

        if server_status == STATUS_DA_THU_HOI:
            return False, (
                "Quyền sử dụng ứng dụng này không còn hiệu lực. "
                "Vui lòng liên hệ TB."
            )
        elif server_status == STATUS_TAM_NGUNG:
            return False, (
                "Quyền sử dụng ứng dụng tạm thời bị tạm ngưng. "
                "Vui lòng liên hệ TB."
            )
        return True, "Hợp lệ."

    # Không kết nối được — dùng cache
    if cache.status in (STATUS_DA_THU_HOI, STATUS_TAM_NGUNG):
        return False, (
            "Quyền sử dụng không hợp lệ. Vui lòng liên hệ TB."
        )
    return True, "Hợp lệ (offline)."
