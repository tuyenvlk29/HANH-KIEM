# Hệ thống tổng hợp hạnh kiểm / rèn luyện

Đây là thư mục dự án chạy hoàn toàn trên máy tính cá nhân. Dữ liệu học sinh không được thiết kế để tải lên dịch vụ đám mây.

## Trạng thái đã lưu

- Đã lưu nguyên vẹn 9 tệp nguồn tháng 9 trong `sources_original/`.
- Có danh sách mã SHA-256 trong `SOURCE_MANIFEST.md` để kiểm tra tệp gốc không bị thay đổi.
- Có yêu cầu nghiệp vụ đầy đủ trong `PROJECT_CONTEXT.md`.
- Có prompt sẵn để tiếp tục trong một phiên Codex local mới tại `PROMPT_TIEP_TUC.md`.
- Có lệnh kiểm tra bộ tệp tại `commands/KIEM_TRA_FILE_GOC.ps1`.
- Đã có V2 đa lớp chạy local trong `app/`, giao diện mở bằng `CHAY_HE_THONG.cmd`.
- Ứng dụng tự lấy lớp, sĩ số và điểm nền từ file mẫu của lớp được chọn; không khóa theo một lớp cụ thể.
- Đọc được báo cáo vi phạm `.xlsx` và báo cáo chi tiết VnEdu `.xlsx`/`.xls`; VnEdu `.xls` được đọc trực tiếp, không cần Microsoft Excel.
- Có chế độ VnEdu theo tháng: lưu mẫu của mỗi lớp một lần trong `ho_so_lop/`, sau đó mỗi tháng chỉ cần chọn báo cáo VnEdu mới của lớp.
- Ba mục điểm nền hiển thị riêng là Học tập, Chuyên cần và Tác phong/đồng phục (`+0,25đ` mỗi mục/tuần đủ điều kiện). Vắng học không cộng cả ba; lỗi đồng phục chỉ không cộng Tác phong/đồng phục; đi trễ đơn thuần không bị coi là vắng.
- Bản quyền giao diện: **Tuyên Bùi**.

## Nguyên tắc bắt buộc

1. Không chỉnh sửa trực tiếp bất kỳ tệp nào trong `sources_original/`.
2. Mọi tệp làm việc phải được sao chép sang `work/`.
3. Mọi tệp giao cho giáo viên phải đặt trong `outputs/`.
4. Không gửi dữ liệu học sinh lên dịch vụ đám mây.
5. Điểm chỉ do bảng quy tắc xác định; không dùng AI để tự đoán số điểm.
6. Trường hợp tên hoặc giao dịch không chắc chắn phải đưa vào danh sách GVCN xác nhận.

## Tiếp tục dự án

Mở Codex local tại thư mục này, sau đó dán toàn bộ nội dung trong `PROMPT_TIEP_TUC.md`.

Để chạy hệ thống, nhấp đúp `CHAY_HE_THONG.cmd` và làm theo `HUONG_DAN_SU_DUNG.md`.

Kiểm tra tệp gốc trong PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\commands\KIEM_TRA_FILE_GOC.ps1
```
