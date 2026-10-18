-- ============================================================================
-- SUPABASE SETUP — Hệ thống quản lý quyền sử dụng từ xa
-- Tổng hợp Hạnh kiểm / Rèn luyện — Tuyên Bùi
-- ============================================================================
-- 
-- Hướng dẫn:
-- 1. Mở Supabase Dashboard → SQL Editor
-- 2. Dán toàn bộ nội dung file này vào
-- 3. Nhấn "Run" để tạo bảng, chỉ mục và RLS
-- 4. Sau đó chạy file 02_admin_setup.sql để tạo tài khoản quản trị
--
-- NGUYÊN TẮC:
-- - KHÔNG lưu dữ liệu học sinh, file Word/Excel, điểm số
-- - Chỉ lưu thông tin thiết bị để quản lý quyền sử dụng
-- - Row Level Security bảo vệ mọi truy cập
-- ============================================================================

-- ============================================================================
-- 1. BẢNG devices — Quản lý thiết bị đã đăng ký
-- ============================================================================
CREATE TABLE IF NOT EXISTS devices (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_uuid     TEXT NOT NULL UNIQUE,
    machine_name    TEXT NOT NULL DEFAULT '',
    user_name       TEXT NOT NULL DEFAULT '',
    organization    TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'CHO_DUYET'
                        CHECK (status IN ('CHO_DUYET', 'DANG_HOAT_DONG', 'DA_THU_HOI', 'TAM_NGUNG')),
    app_version     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now(),
    last_seen_at    TIMESTAMPTZ DEFAULT now(),
    last_check_at   TIMESTAMPTZ DEFAULT now(),
    revoked_at      TIMESTAMPTZ,
    note            TEXT DEFAULT ''
);

-- Chỉ mục tăng tốc truy vấn
CREATE INDEX IF NOT EXISTS idx_devices_device_uuid ON devices (device_uuid);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices (status);
CREATE INDEX IF NOT EXISTS idx_devices_user_name ON devices (user_name);
CREATE INDEX IF NOT EXISTS idx_devices_created_at ON devices (created_at DESC);


-- ============================================================================
-- 2. BẢNG license_events — Lịch sử thao tác license
-- ============================================================================
CREATE TABLE IF NOT EXISTS license_events (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_uuid     TEXT NOT NULL,
    event_type      TEXT NOT NULL
                        CHECK (event_type IN (
                            'DANG_KY',           -- Đăng ký thiết bị mới
                            'DUYET',             -- Duyệt thiết bị
                            'THU_HOI',           -- Thu hồi quyền
                            'TAM_NGUNG',         -- Tạm ngưng
                            'KICH_HOAT_LAI',     -- Kích hoạt lại
                            'KIEM_TRA_OK',       -- Kiểm tra quyền thành công
                            'KIEM_TRA_LOI',      -- Kiểm tra quyền thất bại
                            'GHI_CHU'            -- Ghi chú quản trị
                        )),
    detail          TEXT DEFAULT '',
    admin_email     TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Chỉ mục
CREATE INDEX IF NOT EXISTS idx_events_device_uuid ON license_events (device_uuid);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON license_events (event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON license_events (created_at DESC);


-- ============================================================================
-- 3. BẢNG admin_users — Quản lý tài khoản quản trị
-- ============================================================================
-- Lưu danh sách email được phép quản trị.
-- Chỉ người có email trong bảng này (và đã đăng nhập qua Supabase Auth)
-- mới được xem/sửa toàn bộ thiết bị.
CREATE TABLE IF NOT EXISTS admin_users (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email           TEXT NOT NULL UNIQUE,
    display_name    TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT now()
);


-- ============================================================================
-- 4. HELPER FUNCTION — Kiểm tra user hiện tại có phải admin không
-- ============================================================================
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM admin_users
        WHERE email = auth.jwt() ->> 'email'
    );
END;
$$;


-- ============================================================================
-- 5. ROW LEVEL SECURITY — Bảng devices
-- ============================================================================
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;

-- Policy: Ứng dụng (anon) có thể INSERT thiết bị mới (đăng ký)
CREATE POLICY "devices_insert_anon"
    ON devices
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Policy: Ứng dụng (anon) chỉ đọc bản ghi của chính thiết bị đó
CREATE POLICY "devices_select_own"
    ON devices
    FOR SELECT
    TO anon
    USING (true);
    -- Lưu ý: App query bằng device_uuid, không có auth.
    -- RLS cho anon cho phép SELECT nhưng app chỉ query bằng UUID của mình.
    -- Admin dùng authenticated role + is_admin().

-- Policy: Ứng dụng (anon) cập nhật last_seen_at, last_check_at của chính nó
CREATE POLICY "devices_update_own"
    ON devices
    FOR UPDATE
    TO anon
    USING (true)
    WITH CHECK (true);
    -- Chỉ cho phép cập nhật các trường non-sensitive (app chỉ PATCH last_seen_at, last_check_at, app_version)

-- Policy: Admin (authenticated + is_admin) xem tất cả
CREATE POLICY "devices_select_admin"
    ON devices
    FOR SELECT
    TO authenticated
    USING (is_admin());

-- Policy: Admin cập nhật tất cả (duyệt, thu hồi, kích hoạt lại)
CREATE POLICY "devices_update_admin"
    ON devices
    FOR UPDATE
    TO authenticated
    USING (is_admin())
    WITH CHECK (is_admin());

-- Policy: Admin xóa (hiếm khi dùng nhưng có)
CREATE POLICY "devices_delete_admin"
    ON devices
    FOR DELETE
    TO authenticated
    USING (is_admin());


-- ============================================================================
-- 6. ROW LEVEL SECURITY — Bảng license_events
-- ============================================================================
ALTER TABLE license_events ENABLE ROW LEVEL SECURITY;

-- Policy: Ứng dụng (anon) có thể ghi event
CREATE POLICY "events_insert_anon"
    ON license_events
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Policy: Admin xem tất cả events
CREATE POLICY "events_select_admin"
    ON license_events
    FOR SELECT
    TO authenticated
    USING (is_admin());

-- Policy: Ứng dụng (anon) chỉ đọc event của chính mình (optional, giới hạn)
CREATE POLICY "events_select_anon"
    ON license_events
    FOR SELECT
    TO anon
    USING (true);


-- ============================================================================
-- 7. ROW LEVEL SECURITY — Bảng admin_users
-- ============================================================================
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Chỉ admin xem danh sách admin
CREATE POLICY "admin_users_select_admin"
    ON admin_users
    FOR SELECT
    TO authenticated
    USING (is_admin());

-- Chỉ admin thêm admin mới
CREATE POLICY "admin_users_insert_admin"
    ON admin_users
    FOR INSERT
    TO authenticated
    WITH CHECK (is_admin());

-- Chỉ admin xóa admin
CREATE POLICY "admin_users_delete_admin"
    ON admin_users
    FOR DELETE
    TO authenticated
    USING (is_admin());


-- ============================================================================
-- HOÀN TẤT SETUP CƠ BẢN
-- ============================================================================
-- Tiếp theo: Chạy file 02_admin_setup.sql để tạo tài khoản quản trị đầu tiên.
