"""
test_license.py — Kiểm thử hệ thống quản lý quyền sử dụng

Kiểm tra các tình huống:
1. Thiết bị chưa đăng ký → cần đăng ký
2. Thiết bị chờ duyệt → cho phép dùng
3. Thiết bị đã duyệt → cho phép dùng
4. Thiết bị bị thu hồi → chặn + thông báo
5. Mất Internet, còn trong 14 ngày → cho phép offline
6. Mất Internet, quá 14 ngày → chặn + yêu cầu kết nối
7. Cache license hoạt động đúng
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Thêm đường dẫn dự án
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.license_client import (
    LicenseCache,
    LicenseCheckResult,
    STATUS_CHO_DUYET,
    STATUS_DANG_HOAT_DONG,
    STATUS_DA_THU_HOI,
    STATUS_TAM_NGUNG,
    MAX_OFFLINE_DAYS,
    generate_device_uuid,
    get_machine_name,
)


def test_generate_device_uuid():
    """UUID phải cố định theo máy tính (MachineGuid), không đổi khi gọi lại."""
    uuid1 = generate_device_uuid()
    uuid2 = generate_device_uuid()

    assert uuid1 == uuid2, "UUID phải cố định trên cùng một máy tính"
    assert len(uuid1) == 36, "UUID phải có 36 ký tự"
    assert "-" in uuid1, "UUID phải có dấu gạch ngang"
    print("✓ test_generate_device_uuid PASSED")


def test_get_machine_name():
    """Lấy được tên máy tính."""
    name = get_machine_name()
    assert isinstance(name, str), "Tên máy phải là chuỗi"
    assert len(name) > 0, "Tên máy không được rỗng"
    print(f"✓ test_get_machine_name PASSED (máy: {name})")


def test_cache_save_load():
    """Cache lưu và đọc đúng."""
    cache = LicenseCache()
    cache.device_uuid = "test-uuid-1234"
    cache.user_name = "Nguyễn Văn A"
    cache.organization = "Trường THCS ABC"
    cache.status = STATUS_DANG_HOAT_DONG
    cache.last_valid_check = datetime.now().isoformat()
    cache.registered = True
    cache.save()

    loaded = LicenseCache.load()
    assert loaded.device_uuid == "test-uuid-1234"
    assert loaded.user_name == "Nguyễn Văn A"
    assert loaded.organization == "Trường THCS ABC"
    assert loaded.status == STATUS_DANG_HOAT_DONG
    assert loaded.registered is True
    print("✓ test_cache_save_load PASSED")


def test_offline_valid_within_14_days():
    """Trong 14 ngày offline, vẫn hợp lệ."""
    cache = LicenseCache()
    cache.last_valid_check = (datetime.now() - timedelta(days=10)).isoformat()

    assert cache.is_offline_valid() is True, "10 ngày < 14 ngày phải hợp lệ"
    print("✓ test_offline_valid_within_14_days PASSED")


def test_offline_expired_after_14_days():
    """Quá 14 ngày offline, hết hạn."""
    cache = LicenseCache()
    cache.last_valid_check = (datetime.now() - timedelta(days=15)).isoformat()

    assert cache.is_offline_valid() is False, "15 ngày > 14 ngày phải hết hạn"
    print("✓ test_offline_expired_after_14_days PASSED")


def test_needs_online_check_after_24h():
    """Cần kiểm tra online sau 24h."""
    cache = LicenseCache()
    cache.last_valid_check = (datetime.now() - timedelta(hours=25)).isoformat()

    assert cache.needs_online_check() is True, "25h > 24h phải cần check"
    print("✓ test_needs_online_check_after_24h PASSED")


def test_no_check_needed_within_24h():
    """Chính sách mới: luôn kiểm tra online mỗi lần khởi động."""
    cache = LicenseCache()
    cache.last_valid_check = (datetime.now() - timedelta(hours=12)).isoformat()

    assert cache.needs_online_check() is True, "Chính sách mới: luôn check online khi mở app"
    print("✓ test_no_check_needed_within_24h PASSED")


def test_days_since_last_check():
    """Đếm số ngày đúng."""
    cache = LicenseCache()
    cache.last_valid_check = (datetime.now() - timedelta(days=5)).isoformat()

    days = cache.days_since_last_check()
    assert days == 5, f"Phải là 5 ngày, nhưng ra {days}"
    print("✓ test_days_since_last_check PASSED")


def test_revoked_device_message():
    """Thiết bị bị thu hồi phải hiện thông báo tiếng Việt đúng."""
    from unittest.mock import patch
    cache = LicenseCache()
    cache.device_uuid = "test-revoked"
    cache.status = STATUS_DA_THU_HOI
    cache.registered = True
    cache.last_valid_check = datetime.now().isoformat()
    cache.save()

    # Giả lập offline (mạng không kết nối)
    from app.license_client import check_license
    with patch("app.license_client._make_request", return_value=(0, None)):
        result = check_license("test-revoked")

    assert result.allowed is False, "Thiết bị thu hồi phải bị chặn"
    assert "không còn hiệu lực" in result.message, \
        f"Thông báo phải chứa 'không còn hiệu lực', nhưng ra: {result.message}"
    assert "liên hệ TB" in result.message, \
        f"Thông báo phải chứa 'liên hệ TB', nhưng ra: {result.message}"
    print("✓ test_revoked_device_message PASSED")


def test_unregistered_device():
    """Thiết bị chưa đăng ký trên server phải yêu cầu đăng ký."""
    from unittest.mock import patch
    from app.license_client import clear_license_cache, check_license
    clear_license_cache()

    with patch("app.license_client._make_request", return_value=(200, [])):
        result = check_license()
        assert result.need_registration is True, "Chưa đăng ký phải cần đăng ký"
    print("✓ test_unregistered_device PASSED")


def test_pending_device_allowed():
    """Thiết bị chờ duyệt vẫn cho phép dùng khi offline."""
    from unittest.mock import patch
    cache = LicenseCache()
    cache.device_uuid = "test-pending"
    cache.status = STATUS_CHO_DUYET
    cache.registered = True
    cache.last_valid_check = datetime.now().isoformat()
    cache.save()

    from app.license_client import check_license
    with patch("app.license_client._make_request", return_value=(0, None)):
        result = check_license("test-pending")

    assert result.allowed is True, "Chờ duyệt phải được phép dùng"
    assert "offline" in result.message.lower() or "chờ" in result.message.lower(), "Thông báo phải hợp lệ"
    print("✓ test_pending_device_allowed PASSED")


def test_no_supabase_config_allows_app():
    """Khi chưa cấu hình Supabase, app vẫn chạy bình thường."""
    # Temporarily remove env vars
    old_url = os.environ.pop("SUPABASE_URL", None)
    old_key = os.environ.pop("SUPABASE_ANON_KEY", None)

    from app.license_client import get_supabase_config
    url, key = get_supabase_config()

    # Restore
    if old_url:
        os.environ["SUPABASE_URL"] = old_url
    if old_key:
        os.environ["SUPABASE_ANON_KEY"] = old_key

    # Nếu không có .env file thì URL sẽ là None → app vẫn chạy
    print(f"✓ test_no_supabase_config: URL={'có' if url else 'chưa cấu hình'}")


def test_license_monitor_detects_revocation():
    """LicenseMonitor phải phát hiện khi thiết bị bị thu hồi hoặc tạm ngưng."""
    from unittest.mock import MagicMock, patch
    from app.license_ui import LicenseMonitor
    from app.license_client import LicenseCheckResult, STATUS_TAM_NGUNG

    mock_root = MagicMock()
    monitor = LicenseMonitor(mock_root, interval_seconds=1)

    fake_result = LicenseCheckResult()
    fake_result.allowed = False
    fake_result.status = STATUS_TAM_NGUNG
    fake_result.message = "Quyền sử dụng tạm thời bị tạm ngưng."

    with patch("app.license_client.check_license", return_value=fake_result):
        monitor._check_once()

    # Phải gọi self.root.after(...) để khóa app trên main thread
    assert mock_root.after.called, "Khi quyền bị từ chối, monitor phải gọi root.after để khóa app"
    print("✓ test_license_monitor_detects_revocation PASSED")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 60)
    print("KIEM THU HE THONG QUAN LY QUYEN SU DUNG")
    print("=" * 60)
    print()

    tests = [
        test_generate_device_uuid,
        test_get_machine_name,
        test_cache_save_load,
        test_offline_valid_within_14_days,
        test_offline_expired_after_14_days,
        test_needs_online_check_after_24h,
        test_no_check_needed_within_24h,
        test_days_since_last_check,
        test_unregistered_device,
        test_pending_device_allowed,
        test_revoked_device_message,
        test_no_supabase_config_allows_app,
        test_license_monitor_detects_revocation,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"X {test_fn.__name__} FAILED: {e}")

    print()
    print("=" * 60)
    print(f"Ket qua: {passed}/{passed + failed} tests passed")
    if failed == 0:
        print("TAT CA TESTS DEU PASS!")
    else:
        print(f"CO {failed} TEST(S) THAT BAI")
    print("=" * 60)

