-- ============================================================================
-- ADMIN SETUP — Tạo tài khoản quản trị đầu tiên
-- ============================================================================
--
-- HƯỚNG DẪN:
--
-- Bước 1: Tạo tài khoản Supabase Auth
--   - Vào Supabase Dashboard → Authentication → Users
--   - Nhấn "Add user" → "Create new user"
--   - Nhập email và mật khẩu cho tài khoản quản trị
--   - ✅ Tích "Auto Confirm User"
--
-- Bước 2: Thêm email vào bảng admin_users
--   - Thay 'your-admin-email@example.com' bằng email thật của bạn
--   - Chạy câu SQL bên dưới trong SQL Editor
--
-- Bước 3: Kiểm tra
--   - Đăng nhập vào công cụ quản trị bằng email/password đã tạo
--   - Nếu đăng nhập thành công và thấy danh sách thiết bị, setup đúng.
--
-- ============================================================================

-- ⚠️ THAY ĐỔI EMAIL DƯỚI ĐÂY TRƯỚC KHI CHẠY!
INSERT INTO admin_users (email, display_name)
VALUES (
    'your-admin-email@example.com',   -- ← Thay bằng email quản trị thật
    'Quản trị viên'                   -- ← Tên hiển thị (tùy chọn)
)
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- Kiểm tra đã thêm thành công chưa:
-- ============================================================================
-- SELECT * FROM admin_users;
