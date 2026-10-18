# Prompt tiếp tục dự án trong Codex local

Tiếp tục xây dựng dự án trong thư mục hiện tại. Hãy đọc `README.md`, `PROJECT_CONTEXT.md`, `SOURCE_MANIFEST.md` và toàn bộ 9 tệp trong `sources_original/` trước khi triển khai.

Mục tiêu là tiếp tục hoàn thiện hệ thống tổng hợp hạnh kiểm/rèn luyện đa lớp chạy hoàn toàn LOCAL trên PC. Không tải dữ liệu học sinh hay tệp nguồn lên dịch vụ đám mây. Không chỉnh sửa trực tiếp các tệp trong `sources_original/`; trước mọi xử lý phải sao chép sang `work/`.

Dùng bộ tháng 9 làm dữ liệu kiểm thử chuẩn. Xây hệ thống có giao diện đơn giản cho giáo viên: chọn hoặc thả tệp nguồn, bấm Tổng hợp, xem danh sách cần GVCN xác nhận, rồi xuất Excel đúng cấu trúc file mẫu đã chọn. Tuyệt đối không ghi cứng lớp hay sĩ số trong mã nguồn.

V1 phải: đọc Excel/Word; khóa danh sách chuẩn 47 HS; tạo mã HS và bí danh; chuẩn hóa/đối chiếu tên và lớp; tổng hợp điểm gốc + điểm cộng + điểm trừ theo bảng quy tắc; chống trùng; áp trần điểm cộng +10/HS/tháng; lưu nguồn và minh chứng cho từng giao dịch; không tự quyết định trường hợp mơ hồ; xuất danh sách `CẦN GVCN XÁC NHẬN`; và tạo file kết quả có thể truy vết.

Đã hỗ trợ thêm báo cáo chi tiết VnEdu: nhận dạng tệp `.xlsx` và `.xls` theo các cột Họ và tên, Lớp, Hình thức, Ngày; kế thừa tên/lớp ở các dòng tiếp diễn; bỏ qua nghỉ có phép; đối chiếu các nhãn VnEdu ngắn với tiêu chí chính thức; chuyển hành vi chưa rõ sang `CAN_GVCN_XAC_NHAN`. VnEdu `.xls` được đọc trực tiếp bằng thư viện `xlrd` đã đóng gói, không cần Excel.

Đã có chế độ tháng mới: GVCN bấm `THIẾT LẬP MẪU LỚP` một lần để lưu bản sao file mẫu trong `ho_so_lop/`. Các tháng sau chỉ cần chọn đúng file VnEdu của lớp; hệ thống tự nhận lớp và tháng, rồi xuất kết quả. Điểm cộng chỉ được áp dụng nếu file VnEdu có nội dung khớp trực tiếp tiêu chí cộng; không tự tạo điểm cộng khi không có minh chứng.

Yêu cầu định dạng đầu ra: cột `HÀNH VI CẦN CẢI THIỆN` phải ghi mỗi giao dịch trên một dòng, mở đầu bằng `-`. Nếu có điểm trừ đã áp dụng, kèm điểm theo tiêu chí dùng dấu phẩy thập phân Việt Nam; nếu không có điểm trừ thì chỉ ghi hành vi. Không gộp các giao dịch bằng dấu chấm phẩy.

Chống trùng đã chốt thêm: nếu cùng một loại lỗi của cùng học sinh đã có ngày cụ thể trong tháng thì mọi bản ghi cùng lỗi thiếu ngày bị loại bỏ hoàn toàn khỏi tính điểm, cột hành vi và danh sách GVCN xác nhận. So trùng theo loại hành vi chuẩn hóa, không theo mã quy tắc hoặc cách diễn đạt của nguồn; xem `Trễ sáng`/`Đi học trễ` và `Không phù hiệu`/`Không phù hệu` là cùng loại. Chỉ lưu lại ở `GIAO_DICH_DIEM` với trạng thái `LOAI_BO_TRUNG_KHONG_NGAY` để truy vết.

Quy tắc nghiệp vụ đã chốt: mỗi tuần đủ điều kiện, ba mục nền Học tập, Chuyên cần và Tác phong/đồng phục có mức `+0,25đ` mỗi mục. Nếu học sinh vắng học trong một tuần, bất kể có phép hay không phép, không cộng cả ba mục này. Đi trễ đơn thuần không phải vắng học. Không phù hiệu hoặc lỗi đồng phục chỉ không cộng Tác phong/đồng phục, không làm mất Học tập hoặc Chuyên cần. Không cộng bù các mục không đủ điều kiện; lưu giao dịch với điểm áp dụng 0 và trạng thái `KHONG_DU_DIEU_KIEN`. Hoạt động có minh chứng riêng từ nguồn khác vẫn được tính. Các điểm trừ học tập chỉ áp dụng khi có nguồn/minh chứng và tiêu chí.

Hãy triển khai thực tế, chạy kiểm thử bằng các tệp tháng 9 và báo cáo VnEdu mẫu, đối chiếu với file mẫu, sửa lỗi cho đến khi luồng chạy được. Lưu mã nguồn và tài liệu trong thư mục dự án; chỉ lưu tệp giao cho người dùng trong `outputs/`. Trước khi kết thúc, cung cấp hướng dẫn bấm/chạy ngắn gọn cho giáo viên và báo rõ các quy tắc nghiệp vụ còn cần GVCN chốt.
