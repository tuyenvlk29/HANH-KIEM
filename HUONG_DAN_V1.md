# Hướng dẫn sử dụng hệ thống

## Chạy hệ thống

Nhấp đúp `CHAY_HE_THONG_V1.cmd`.

Có thể chạy trực tiếp trong thư mục dự án hoặc sau khi giải nén gói V1 trong thư mục `outputs`. Hệ thống sẽ tự tìm thư mục dự án và bộ dữ liệu tháng 9 nếu chúng vẫn nằm cùng cây thư mục.

Trong cửa sổ hiện ra:

1. Chọn thư mục chứa các file nguồn của tháng.
2. Chọn thư mục lưu kết quả.
3. Bấm `TỔNG HỢP`.
4. Mở file kết quả và xem sheet `CAN_GVCN_XAC_NHAN` trước khi sử dụng chính thức.

## Các sheet trong file kết quả

- Sheet kết quả theo đúng cấu trúc file mẫu mà giáo viên đã chọn.
- `DANH_SACH_HS`: danh sách chuẩn và mã học sinh.
- `GIAO_DICH_DIEM`: từng khoản cộng/trừ, nguồn, minh chứng, mã chống trùng và trạng thái.
- `CAN_GVCN_XAC_NHAN`: tên, quy tắc hoặc dữ liệu mà hệ thống không được phép tự đoán.
- `QUY_TAC_V1`: các quy tắc đang được máy áp dụng.
- `NHAT_KY_TONG_HOP`: thông tin lần chạy và danh sách file nguồn.

## Quy tắc an toàn

- Hệ thống không chỉnh sửa file nguồn.
- Tổng điểm cộng được giới hạn tối đa +10 mỗi học sinh mỗi tháng.
- Giao dịch nghi trùng chỉ được áp dụng một lần.
- Nội dung chưa có quy tắc rõ được đưa vào `CAN_GVCN_XAC_NHAN` và tạm tính 0 điểm.
- Hệ thống dò mọi file Word `.doc` và `.docx` trong thư mục đã chọn, không phụ thuộc tên tổ/bộ phận.
- Với file `.doc` cũ, hệ thống dùng Microsoft Word cài trên máy để chuyển một bản sao tạm sang `.docx`; file gốc không bị sửa. Nếu không chuyển được, lỗi cụ thể sẽ được ghi vào `CAN_GVCN_XAC_NHAN`.
- Nếu bảng Word có cột `Điểm cộng đề nghị`, hệ thống ưu tiên đúng số điểm trong cột này và lưu nguyên nội dung hoạt động vào minh chứng.
