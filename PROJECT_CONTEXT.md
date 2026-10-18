# Bối cảnh dự án hệ thống tổng hợp hạnh kiểm / rèn luyện

## Mục tiêu

Xây dựng V2 chạy local trên PC dành cho giáo viên chủ nhiệm nhiều lớp. Mỗi tháng người dùng chọn hoặc thả các tệp Excel và Word nguồn, bấm Tổng hợp, kiểm tra các trường hợp cần xác nhận, rồi xuất tệp Excel đúng cấu trúc file mẫu đã chọn. Lớp, sĩ số và điểm nền không được ghi cứng trong mã nguồn.

## Quyền riêng tư

- Toàn bộ dữ liệu học sinh và tệp nguồn chỉ được xử lý cục bộ.
- Không thiết kế luồng tải dữ liệu học sinh lên dịch vụ đám mây.
- Không sửa tệp nguồn gốc. Luôn tạo bản sao làm việc trước khi xử lý.

## Bộ kiểm thử chuẩn tháng 9

Chín tệp gốc nằm trong `sources_original/`:

1. `12C7_HẠNH KIỂM THANG 9.xlsx`: mẫu đầu ra 47 học sinh, 10 cột.
2. `12C07 - DANH GIA DIEM HK THANG -HS - LQDLBT - 2026 - 2027.xlsx`: dữ liệu điểm theo tuần và tháng.
3. `Tổng hợp vi phạm 3 khối tháng 09 năm học 2026 _ 2027.xlsx`: nguồn vi phạm.
4. `Bang_cong_diem_hanh_vi_tich_cuc_thang_9.docx`: bảng quy tắc điểm cộng.
5. `BAO_CAO_TINH_HINH_LOP_HANG_THANG.docx`: báo cáo lớp.
6. `BÁO CÁO TÌNH HÌNH NỀ NẾP 3 KHỐI TUẦN 04 THÁNG 09.docx`: báo cáo nề nếp.
7. `Lễ Tân Thống kê điểm cộng trừ từ các bộ phận.doc`: nguồn hoạt động.
8. `Thư viện- Thống kê điểm trừ- cộng từ các bộ phận.doc`: nguồn hoạt động.
9. `Tổ Toán - Thống kê điểm cộng các bộ phận.doc`: nguồn hoạt động.

Mẫu kiểm thử bổ sung: báo cáo chi tiết VnEdu `mẫu vi pham từ vnedu.xlsx`, sheet `hs_chi_tiet`, có các cột Họ và tên, Lớp, Hình thức, Ghi chú, Ngày. Các dòng tiếp diễn có thể bỏ trống tên và lớp; phải kế thừa thông tin của học sinh ở dòng trước. Báo cáo VnEdu `.xls` cũ được đọc trực tiếp bằng `xlrd`; tuyệt đối không sửa file gốc và không cần Microsoft Excel.

## Những gì đã xác định từ bộ dữ liệu

- Mẫu đầu ra có 47 học sinh và các cột: STT, Họ tên, Lớp, Biểu hiện tích cực, Điểm cộng, Hành vi cần cải thiện, Điểm trừ, Tổng điểm, Xếp loại, Nhận xét.
- Điểm khởi đầu trong mẫu là 80.
- Sheet `XET THANG` trong workbook đánh giá có danh sách 47 học sinh phù hợp với mẫu; sheet `Lớp_12C07` có danh sách khác và chỉ có 45 tên thực. Danh sách chuẩn phải được khóa từ một nguồn duy nhất.
- Tên trong nguồn có thể viết tắt, ví dụ `Ngọc Diệp`, `Gia Bảo`, `Minh Thùy`; hệ thống cần mã học sinh nội bộ và bảng bí danh.
- Quy tắc điểm cộng tháng 9 có các mục như học tập tốt 5 tuần +1,25; chuyên cần tốt +1,25; tác phong tốt +1,25; poster +1; nhật ký lòng biết ơn +0,25; nhiệm vụ họp PHHS +1; cán bộ lớp +1 hoặc +2 tùy mức độ.
- Không cộng trùng. Cùng hoạt động có nhiều mức thì lấy mức cao nhất. Hoạt động phải có minh chứng. Tổng điểm cộng tối đa +10 điểm mỗi học sinh mỗi tháng.
- Quy tắc nền theo tuần: mỗi mục Học tập, Chuyên cần và Tác phong/đồng phục có mức `+0,25đ` khi đủ điều kiện. Hễ có vắng học, có phép hoặc không phép, thì không cộng cả ba mục của tuần đó. Đi trễ đơn thuần không phải vắng học. Không phù hiệu hoặc lỗi đồng phục chỉ làm không cộng Tác phong/đồng phục, không làm mất Học tập hoặc Chuyên cần. Các điểm hoạt động có minh chứng riêng vẫn được xử lý độc lập.

## Phạm vi hiện tại

1. Đọc các tệp `.xlsx`, `.docx` và `.doc` nguồn.
2. Khóa danh sách chuẩn 47 học sinh và gán mã nội bộ.
3. Chuẩn hóa tên, lớp và bí danh; không tự ghép khi độ chắc chắn thấp.
4. Tổng hợp điểm gốc, điểm cộng hoạt động và điểm trừ vi phạm theo bảng quy tắc.
5. Chống giao dịch trùng theo học sinh, ngày, nội dung, nguồn và mã minh chứng.
6. Áp trần tổng điểm cộng +10 mỗi học sinh mỗi tháng, trừ khi tiêu chí/quy định được cập nhật khác.
7. Lưu sổ giao dịch có nguồn và minh chứng cho từng khoản cộng/trừ.
8. Đưa tên, giao dịch hoặc quy tắc mơ hồ vào danh sách `CẦN GVCN XÁC NHẬN`.
9. Xuất đúng cấu trúc mẫu tháng 9 và có khả năng giải thích công thức `80 + điểm cộng - điểm trừ`.
10. Có giao diện đơn giản để chọn/thả tệp và bấm Tổng hợp.

## Cấu trúc dữ liệu trung gian đề xuất

Mỗi giao dịch cần có tối thiểu: mã giao dịch, mã học sinh, họ tên chuẩn, lớp, ngày, tháng, nguồn tệp, vị trí nguồn, nội dung gốc, nội dung chuẩn hóa, loại cộng/trừ, mã quy tắc, điểm đề nghị, điểm được áp dụng, trạng thái xác nhận, mã chống trùng và ghi chú.

## Kiểm toán bắt buộc

- Tên học sinh chưa xác định được.
- Học sinh nguồn không thuộc lớp trong file mẫu.
- Hoạt động hoặc vi phạm nghi trùng.
- Điểm cộng vượt trần +10.
- Điểm đề nghị không khớp bảng quy tắc.
- Khác biệt danh sách học sinh giữa các nguồn.
- Học sinh chuẩn không có dữ liệu nguồn.
- Dòng nguồn thiếu ngày, lớp, nội dung hoặc minh chứng cần thiết.

## Kiểm thử VnEdu đã hoàn thành

- Đã đọc trực tiếp file mẫu VnEdu: 26 giao dịch thuộc lớp mẫu.
- 21 giao dịch được áp dụng điểm theo tiêu chí; tổng điểm trừ áp dụng từ nguồn VnEdu là 16,5 điểm.
- 5 hành vi chưa có tiêu chí rõ ràng được đưa vào `CAN_GVCN_XAC_NHAN` với điểm áp dụng bằng 0.
- Nghỉ có phép được bỏ qua, không bị xem là vi phạm hạnh kiểm.
- Cột hành vi cần cải thiện được xuất theo từng giao dịch: mỗi dòng có dấu `-`; giao dịch có điểm trừ ghi điểm đã áp dụng, giao dịch vắng hoặc vi phạm không bị trừ điểm chỉ ghi nội dung; không gộp các hành vi bằng dấu chấm phẩy.
- Với điểm tuần, giao dịch thuộc ba mục nền bị ghi `KHONG_DU_DIEU_KIEN` và điểm áp dụng bằng 0 khi học sinh vắng học; hệ thống không tạo khoản cộng bù. Các lỗi học tập có điểm trừ chỉ được áp dụng khi có trong nguồn hoặc tiêu chí.

## Tiêu chí hoàn thành

- Chạy hoàn toàn local và không sửa các tệp gốc.
- Đọc thành công toàn bộ bộ tháng 9.
- Danh sách chuẩn đúng 47 học sinh.
- Có sổ giao dịch truy vết được về nguồn.
- Có danh sách GVCN xác nhận.
- Có kiểm thử chống trùng và trần điểm cộng.
- Xuất được Excel đúng cấu trúc mẫu và kiểm tra trực quan không lỗi bố cục.
- Có hướng dẫn ngắn, phù hợp với giáo viên không chuyên kỹ thuật.
