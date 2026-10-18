# Hướng dẫn thiết lập Hệ thống Quản lý Quyền sử dụng từ xa

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Tạo Supabase Project Free](#2-tạo-supabase-project-free)
3. [Chạy SQL tạo bảng và bảo mật](#3-chạy-sql-tạo-bảng-và-bảo-mật)
4. [Tạo tài khoản quản trị](#4-tạo-tài-khoản-quản-trị)
5. [Cấu hình ứng dụng giáo viên](#5-cấu-hình-ứng-dụng-giáo-viên)
6. [Cấu hình công cụ quản trị](#6-cấu-hình-công-cụ-quản-trị)
7. [Đóng gói .exe](#7-đóng-gói-exe)
8. [Vận hành hằng ngày](#8-vận-hành-hằng-ngày)
9. [Xử lý sự cố](#9-xử-lý-sự-cố)

---

## 1. Tổng quan

### Hệ thống hoạt động thế nào?

```
┌─────────────────────────────┐     ┌─────────────────────────┐
│  Ứng dụng Giáo viên (.exe) │────▶│  Supabase Cloud (Free)  │
│                             │     │                         │
│  • Tổng hợp hạnh kiểm      │     │  Bảng devices:          │
│    (100% offline trên máy)  │     │  - tên, đơn vị, trạng   │
│                             │     │    thái, lần dùng gần    │
│  • Chỉ gửi lên:            │     │    nhất                  │
│    - Tên người dùng         │     │                         │
│    - Đơn vị/trường          │     │  KHÔNG lưu:             │
│    - Tên máy tính           │     │  - Dữ liệu học sinh    │
│    - Mã thiết bị UUID       │     │  - File Word/Excel      │
│                             │     │  - Điểm số              │
│  KHÔNG gửi:                 │     │  - Kết quả tổng hợp    │
│  - Dữ liệu học sinh        │     └────────────┬────────────┘
│  - File Word/Excel          │                  │
│  - Điểm hạnh kiểm          │                  │
│  - MAC address, Wi-Fi, GPS  │     ┌────────────▼────────────┐
└─────────────────────────────┘     │  Công cụ Quản trị       │
                                    │  (chỉ dành cho bạn)     │
                                    │                         │
                                    │  • Xem danh sách thiết  │
                                    │    bị đã đăng ký        │
                                    │  • Duyệt / Thu hồi /    │
                                    │    Tạm ngưng / Kích     │
                                    │    hoạt lại             │
                                    │  • Xem lịch sử thao tác│
                                    └─────────────────────────┘
```

### Dữ liệu an toàn

| ✅ Được gửi lên Supabase | ❌ KHÔNG BAO GIỜ gửi |
|---|---|
| Họ tên người dùng | Dữ liệu học sinh |
| Đơn vị/trường | File Word/Excel |
| Tên máy tính | Điểm số, hạnh kiểm |
| Mã thiết bị UUID (ngẫu nhiên) | Kết quả tổng hợp |
| Phiên bản app | MAC address |
| Trạng thái hoạt động | Vị trí GPS, tên Wi-Fi |

---

## 2. Tạo Supabase Project Free

### Bước 2.1: Tạo tài khoản Supabase

1. Truy cập https://supabase.com
2. Nhấn **"Start your project"**
3. Đăng nhập bằng GitHub hoặc email

### Bước 2.2: Tạo project mới

1. Nhấn **"New Project"**
2. Chọn tổ chức (organization) — tạo mới nếu chưa có
3. Điền thông tin:
   - **Name**: `HanhKiem-License` (hoặc tên bạn muốn)
   - **Database Password**: Tạo mật khẩu mạnh → **GHI NHỚ LẠI**
   - **Region**: Chọn **Southeast Asia (Singapore)** cho tốc độ tốt nhất
   - **Pricing Plan**: **Free** (đủ dùng)
4. Nhấn **"Create new project"**
5. Đợi 1-2 phút để Supabase khởi tạo

### Bước 2.3: Lấy URL và Anon Key

1. Vào **Settings** → **API** (menu bên trái)
2. Sao chép:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGci...` (chuỗi dài)
3. **KHÔNG sao chép** `service_role key` — không cần dùng trong ứng dụng

---

## 3. Chạy SQL tạo bảng và bảo mật

### Bước 3.1: Mở SQL Editor

1. Trong Supabase Dashboard, nhấn **"SQL Editor"** (menu bên trái)
2. Nhấn **"New query"**

### Bước 3.2: Chạy schema SQL

1. Mở file `supabase/01_schema.sql` trong dự án
2. Sao chép **TOÀN BỘ** nội dung
3. Dán vào SQL Editor
4. Nhấn **"Run"** (hoặc Ctrl+Enter)
5. Kiểm tra: Không có lỗi đỏ

### Bước 3.3: Kiểm tra bảng đã tạo

1. Vào **Table Editor** (menu bên trái)
2. Phải thấy 3 bảng:
   - `devices`
   - `license_events`
   - `admin_users`

---

## 4. Tạo tài khoản quản trị

### Bước 4.1: Tạo user quản trị trong Supabase Auth

1. Vào **Authentication** → **Users** (menu bên trái)
2. Nhấn **"Add user"** → **"Create new user"**
3. Nhập:
   - **Email**: Email quản trị của bạn (ví dụ: `tuyenbui@example.com`)
   - **Password**: Mật khẩu mạnh → **GHI NHỚ LẠI**
   - ✅ Tích **"Auto Confirm User"**
4. Nhấn **"Create user"**

### Bước 4.2: Thêm email vào bảng admin_users

1. Vào **SQL Editor** → **"New query"**
2. Mở file `supabase/02_admin_setup.sql`
3. **THAY** `your-admin-email@example.com` bằng email bạn vừa tạo ở Bước 4.1
4. Dán vào SQL Editor và nhấn **"Run"**
5. Kiểm tra: Vào **Table Editor** → `admin_users` → phải thấy email của bạn

---

## 5. Cấu hình ứng dụng giáo viên

### Bước 5.1: Tạo file .env

1. Sao chép file `.env.example` thành `.env`:
   ```
   copy .env.example .env
   ```
2. Mở file `.env` và điền thông tin thật:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_ANON_KEY=eyJhbGci...your-real-anon-key
   ```
3. Lưu file

### Bước 5.2: Kiểm thử

```
py -3 tests/test_license.py
```

Kết quả mong đợi: `12/12 tests passed`

### Bước 5.3: Chạy thử ứng dụng

```
py -3 app/main.py
```

- Lần đầu: Hiện form **"Đăng ký thiết bị"**
- Nhập họ tên, đơn vị → nhấn Đăng ký
- Ứng dụng mở bình thường, trạng thái "Chờ duyệt"

---

## 6. Cấu hình công cụ quản trị

### Bước 6.1: Chạy công cụ quản trị

```
py -3 admin/admin_dashboard.py
```

### Bước 6.2: Đăng nhập

- Nhập email và mật khẩu đã tạo ở Bước 4.1
- Nhấn **Đăng nhập**

### Bước 6.3: Duyệt thiết bị

- Trong danh sách, chọn thiết bị có trạng thái "⏳ Chờ duyệt"
- Nhấn nút **"✓ Duyệt"** ở panel bên phải
- Xác nhận → Thiết bị chuyển sang "✅ Đang hoạt động"

---

## 7. Đóng gói .exe

### 7.1: Đóng gói ứng dụng giáo viên

**Quan trọng**: Đặt file `.env` cạnh file `.exe` sau khi đóng gói.

```bash
py -3 -m PyInstaller HeThong_HanhKiem_RenLuyen_TuyenBui.spec
```

Sau khi đóng gói:
```
dist/
  HeThong_HanhKiem_RenLuyen_TuyenBui.exe
```

Khi phân phối, đặt file `.env` cùng thư mục với `.exe`:
```
📁 (thư mục giao cho giáo viên)
  HeThong_HanhKiem_RenLuyen_TuyenBui.exe
  .env                                    ← chứa SUPABASE_URL và ANON_KEY
  📁 quy_tac/
    TIEU_CHI_HANH_KIEM.xlsx
```

### 7.2: Đóng gói công cụ quản trị

```bash
py -3 -m PyInstaller QuanTri_QuyenSuDung_TuyenBui.spec
```

Sau khi đóng gói:
```
dist/
  QuanTri_QuyenSuDung_TuyenBui.exe
```

Đặt file `.env` cạnh file `.exe` quản trị:
```
📁 (thư mục của bạn — KHÔNG PHÂN PHỐI)
  QuanTri_QuyenSuDung_TuyenBui.exe
  .env
```

---

## 8. Vận hành hằng ngày

### 8.1: Luồng hoạt động

```
Giáo viên mở app
    │
    ├─ Lần đầu? → Hiện form đăng ký → Giáo viên nhập tên, đơn vị
    │                                    → Trạng thái: CHO_DUYET
    │
    ├─ Có Internet?
    │   ├─ Có → Kiểm tra trạng thái trên Supabase
    │   │       ├─ DANG_HOAT_DONG → Cho dùng bình thường
    │   │       ├─ CHO_DUYET      → Cho dùng (chờ bạn duyệt)
    │   │       ├─ DA_THU_HOI     → Chặn + thông báo tiếng Việt
    │   │       └─ TAM_NGUNG      → Chặn + thông báo tiếng Việt
    │   │
    │   └─ Không → Dùng cache offline
    │       ├─ < 14 ngày  → Cho dùng bình thường
    │       └─ >= 14 ngày → Yêu cầu kết nối Internet
    │
    └─ App chạy → Tổng hợp hạnh kiểm 100% offline trên máy
```

### 8.2: Việc cần làm thường xuyên

| Tần suất | Việc cần làm |
|---|---|
| Khi có thiết bị mới | Mở công cụ quản trị → Duyệt thiết bị chờ |
| Khi cần thu hồi | Công cụ quản trị → Chọn thiết bị → Thu hồi |
| Hàng tháng (tùy chọn) | Kiểm tra danh sách thiết bị, dọn thiết bị cũ |

### 8.3: Biến môi trường cần điền

| Biến | Nơi dùng | Giá trị |
|---|---|---|
| `SUPABASE_URL` | File `.env` (cạnh exe) | URL từ Supabase Dashboard → Settings → API |
| `SUPABASE_ANON_KEY` | File `.env` (cạnh exe) | Anon key từ Supabase Dashboard → Settings → API |

---

## 9. Xử lý sự cố

### "Không thể đăng ký thiết bị"
- Kiểm tra kết nối Internet
- Kiểm tra file `.env` có đúng `SUPABASE_URL` và `SUPABASE_ANON_KEY` không
- Kiểm tra bảng `devices` trên Supabase đã được tạo chưa

### "Đăng nhập quản trị thất bại"
- Kiểm tra email/mật khẩu đúng (đã tạo ở Bước 4.1)
- Kiểm tra email đã thêm vào bảng `admin_users` (Bước 4.2)
- Kiểm tra RLS đã bật (chạy `01_schema.sql` lại nếu cần)

### "Không thấy thiết bị trong công cụ quản trị"
- Kiểm tra email quản trị có trong bảng `admin_users`
- Kiểm tra RLS policy `devices_select_admin` đã tạo

### "Ứng dụng yêu cầu kết nối sau 14 ngày"
- Đây là thiết kế bình thường: kết nối Internet 1 lần để xác minh
- Sau khi xác minh xong, đếm lại 14 ngày mới cần kết nối

### Chạy ứng dụng không có license (fallback)
- Nếu file `.env` không có hoặc trống → ứng dụng chạy bình thường (không kiểm tra)
- Đây là fallback an toàn để đảm bảo giáo viên không bị gián đoạn
