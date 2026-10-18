# Hướng dẫn sử dụng Hệ thống Tổng hợp Hạnh kiểm / Rèn luyện

✦ **Bản quyền giao diện & hệ thống: © Tuyên Bùi** ✦  
*Ứng dụng chạy hoàn toàn Offline trên máy tính cá nhân — An toàn, bảo mật dữ liệu học sinh tuyệt đối.*

---

## 1. Chuẩn bị dữ liệu

- **Thư mục dữ liệu tháng**: Có thể đặt các file liên quan của lớp trong cùng một thư mục (file mẫu hạnh kiểm/rèn luyện, báo cáo tuần, các quyết định/file Word cộng điểm...).
- **Báo cáo VnEdu**: Chấp nhận file chi tiết dạng `.xlsx` hoặc `.xls` được xuất từ hệ thống VnEdu (chứa các cột *Họ và tên*, *Lớp*, *Hình thức*, *Ngày*).
- **Tính năng tự động**: Hệ thống tự động nhận diện lớp, nhận diện tháng, chống trùng lặp hành vi vi phạm (ví dụ ghi nhận trùng có ngày và không ngày), áp trần điểm cộng tối đa và ghi nhận các trường hợp cần GVCN xác nhận.

---

## 2. Các bước thao tác trên giao diện mới

Giao diện được thiết kế hiện đại, thanh lịch, chia thành 3 bước rõ ràng:

### 🔹 Bước 1 — Chọn dữ liệu & Nơi lưu kết quả
1. **Nguồn dữ liệu**:
   - Bấm **"📄 Chọn file VnEdu..."**: Chọn trực tiếp file Excel báo cáo chi tiết VnEdu của lớp (*khuyên dùng khi đã thiết lập mẫu lớp*).
   - Hoặc bấm **"📁 Chọn thư mục..."**: Chọn thư mục chứa đầy đủ các file dữ liệu trong tháng của lớp.
2. **Thư mục lưu kết quả**:
   - Bấm **"📂 Chọn nơi lưu..."** để chọn thư mục lưu file kết quả mong muốn (mặc định là thư mục `outputs` của chương trình).

### 🔹 Bước 2 — Thiết lập lớp (Làm 1 lần duy nhất cho mỗi lớp)
- Bấm nút **"📋 THIẾT LẬP MẪU LỚP..."** và chọn file Excel mẫu đánh giá hạnh kiểm chuẩn của lớp.
- Hệ thống sẽ tự động đọc và lưu hồ sơ lớp (sĩ số, danh sách học sinh, điểm nền).
- **Từ các tháng tiếp theo**: Thầy/Cô **không cần** làm lại bước này, chỉ cần chọn file VnEdu ở Bước 1!

### 🔹 Bước 3 — Bắt đầu tổng hợp
- Bấm nút **"🚀 TỔNG HỢP"**.
- Trong quá trình chạy, thanh tiến trình sẽ hoạt động sinh động và giao diện **không bao giờ bị treo** (chạy trên tiến trình nền an toàn).
- **Khi hoàn tất**: Bảng thống kê thông minh sẽ hiển thị ngay trên màn hình:
  - 👨‍🎓 **Sĩ số học sinh**
  - 📋 **Tổng số giao dịch** (điểm cộng / trừ)
  - ⚠️ **Mục cần GVCN xác nhận**
  - 🔄 **Giao dịch trùng đã loại bỏ**
  - **Tên & đường dẫn file kết quả**.
- Thầy/Cô có thể bấm ngay:
  - **"📊 Mở file Excel kết quả"** để xem và in kết quả.
  - **"📁 Mở thư mục kết quả"** để mở thư mục lưu trữ file trên máy.

---

## 3. Xử lý các tình huống thường gặp

1. **Thông báo "File Excel đang mở"**:
   - *Nguyên nhân*: File kết quả đang được mở trong phần mềm Microsoft Excel.
   - *Cách xử lý*: Thầy/Cô chỉ cần đóng file Excel đó lại trên thanh tác vụ, sau đó bấm lại nút **"TỔNG HỢP"**.

2. **Thông báo "Chưa có mẫu lớp"**:
   - *Nguyên nhân*: Hệ thống chưa có mẫu sổ của lớp tương ứng với file VnEdu.
   - *Cách xử lý*: Bấm nút **"THIẾT LẬP MẪU LỚP"** ở Bước 2 và chọn file mẫu Excel của lớp, sau đó bấm Tổng hợp lại.

3. **Chưa chọn dữ liệu / Đường dẫn không tồn tại**:
   - Vui lòng bấm các nút **"Chọn file VnEdu..."** hoặc **"Chọn thư mục..."** để chọn đúng file trước khi bấm Tổng hợp.

---

## 4. Cập nhật tiêu chí đánh giá

- Hệ thống đọc file tiêu chí tại: `quy_tac\TIEU_CHI_HANH_KIEM.xlsx`.
- Khi nhà trường có cập nhật khung điểm mới, chỉ cần thay thế file này nhưng giữ nguyên tên file. Sau mỗi lần tổng hợp, Thầy/Cô có thể xem sheet `QUY_TAC` trong file Excel kết quả để kiểm tra các mức điểm đã nạp.

---

## 5. Khởi động ứng dụng

- Nhấp đúp vào file **`CHAY_HE_THONG.cmd`** để mở ứng dụng ngay lập tức.
- Nếu là máy tính mới chưa từng cài Python, hệ thống sẽ tự động cài đặt Python 3.12 từ gói offline có sẵn, không cần kết nối mạng Internet.
