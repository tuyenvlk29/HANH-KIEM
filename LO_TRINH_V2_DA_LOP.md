# Lộ trình V2 — Hệ thống hạnh kiểm/rèn luyện đa lớp, chạy cục bộ

## Mục tiêu

Chuyển bản khởi đầu đơn lớp thành một ứng dụng Windows chạy hoàn toàn trên máy tính, để giáo viên có thể tạo và dùng hồ sơ riêng cho nhiều lớp. Mỗi lần tổng hợp chỉ cần chọn lớp, chọn thư mục nguồn và bấm `TỔNG HỢP`.

Không có bước tải file học sinh lên Internet. File nguồn không bị chỉnh sửa; mọi kết quả, nhật ký và cấu hình nằm trong thư mục dữ liệu mà người dùng chọn.

## Phạm vi V2

- Nhiều lớp, nhiều sĩ số; không cố định số học sinh hoặc mã lớp.
- Mỗi lớp có danh sách học sinh chuẩn, bí danh tên và mẫu Excel đầu ra riêng.
- Thiết lập bằng giao diện: lớp, tháng, điểm nền, trần điểm cộng, file danh sách, file mẫu, thư mục nguồn và thư mục kết quả.
- Lưu cấu hình lớp cục bộ để dùng lại tháng sau.
- Dò các file Word `.doc`, `.docx` và các file Excel theo cấu trúc nguồn đã được hỗ trợ.
- Lấy điểm đề nghị trực tiếp từ bảng Word khi có; lưu nguồn, dòng/bảng và chống trùng giao dịch.
- Bắt buộc xuất danh sách `CẦN GVCN XÁC NHẬN` cho tên, lớp, quy tắc hoặc giao dịch không chắc chắn.
- Giữ tương thích hoàn toàn với các hồ sơ đã tạo trước đó.

## Những điều V2 không tự đoán

- Không tự gán điểm khi không có điểm đề nghị hoặc quy tắc do giáo viên xác nhận.
- Không tự ghép tên mơ hồ khi có từ hai học sinh trở lên cùng khả năng khớp.
- Không tự thay đổi file nguồn, danh sách chuẩn hoặc mẫu Excel.

## Thiết kế dữ liệu

Mỗi lớp được lưu thành một `Hồ sơ lớp` trong thư mục dữ liệu cục bộ:

```text
Du_lieu_hanh_kiem/
  Ho_so_lop/
    LOP_MAU/
      cau_hinh_lop.json
      danh_sach_hoc_sinh.xlsx
      mau_xuat.xlsx
      quy_tac_diem.json
      alias_ten.json
    11A3/
      ...
  Ket_qua/
    2026-10_KET_QUA_HANH_KIEM.xlsx
  Sao_luu/
```

`cau_hinh_lop.json` chỉ lưu thông số không nhạy cảm: mã lớp, tháng/năm mặc định, điểm nền, trần điểm cộng, tên sheet và cách nhận diện cột. Danh sách học sinh và mẫu xuất được sao chép nguyên bản vào hồ sơ lớp để bảo đảm lần tổng hợp sau không phụ thuộc file ngoài.

## Luồng sử dụng cho giáo viên

1. Lần đầu: bấm `TẠO HỒ SƠ LỚP TỪ THƯ MỤC NGUỒN` rồi chọn một thư mục chứa toàn bộ file của lớp.
2. Ứng dụng tự quét để đề xuất file danh sách học sinh chuẩn, file Excel mẫu đầu ra và các file nguồn điểm; giáo viên không phải tách file trước.
3. Giáo viên kiểm tra bảng xem trước: lớp, số học sinh, file mẫu được chọn, tên cột nhận diện và 3 dòng dữ liệu đầu.
4. Nhập điểm nền, trần điểm cộng và xác nhận quy tắc điểm.
5. Lưu hồ sơ lớp.
6. Mỗi tháng: chọn hồ sơ lớp, tháng, thư mục nguồn rồi bấm `TỔNG HỢP`.
7. Kiểm tra sheet `CẦN GVCN XÁC NHẬN`, sau đó mới sử dụng file kết quả.

## Các giai đoạn triển khai

### Giai đoạn 0 — Chốt dữ liệu mẫu và quy tắc (bắt buộc)

- Lấy thêm một bộ dữ liệu thật của một lớp khác, gồm danh sách học sinh, file mẫu và ít nhất một Word cộng điểm + một Excel vi phạm.
- Chốt tên các cột bắt buộc trong danh sách: STT, họ tên, lớp; cho phép giáo viên chọn cột nếu tên khác.
- Chốt quy định điểm nền, trần điểm cộng và thang xếp loại áp dụng chung hay theo từng lớp.
- Đầu ra: hai hồ sơ dữ liệu kiểm thử đã ẩn thông tin nhạy cảm khi cần dùng cho phát triển.

**Tiêu chí đạt:** Bộ dữ liệu kiểm thử hiện có vẫn chạy đúng; bộ lớp thứ hai được đọc đủ danh sách và mẫu, chưa cần tính điểm.

### Giai đoạn 1 — Tách lõi tính điểm khỏi lớp thử nghiệm ban đầu

- Bỏ mọi hằng số về mã lớp, sĩ số và tên sheet tháng khỏi mã nguồn.
- Tạo đối tượng `ClassProfile` nạp từ hồ sơ lớp.
- Chuyển quy tắc điểm và mẫu xếp loại thành cấu hình theo hồ sơ.
- Thêm kiểm tra đầu vào: mã lớp trống, trùng STT, trùng tên, không có học sinh, sai file mẫu.
- Viết kiểm thử cho hai lớp khác nhau chạy cùng một lõi.

**Tiêu chí đạt:** cùng một lệnh có thể tổng hợp hai lớp bằng hai hồ sơ khác nhau; không có mã lớp nào bị ghi cứng trong lõi.

### Giai đoạn 2 — Trình tạo hồ sơ lớp

- Thêm màn hình `TẠO / SỬA HỒ SƠ LỚP`.
- Cho phép chọn một thư mục chứa toàn bộ file lớp; hệ thống tự phân loại các file thành danh sách học sinh, file mẫu, nguồn Word/Excel và file chưa nhận diện.
- Giáo viên chỉ xác nhận hoặc đổi lại file danh sách, file mẫu, lớp, điểm nền, trần điểm cộng và quy tắc khi đề xuất chưa đúng.
- Hiển thị bản xem trước trước khi lưu; yêu cầu giáo viên xác nhận sĩ số và danh sách.
- Sao lưu các file thiết lập vào thư mục hồ sơ, kèm ngày tạo và mã kiểm tra để truy vết.

**Tiêu chí đạt:** một giáo viên không cần sửa mã hay JSON vẫn tạo được hồ sơ cho lớp mới trong giao diện.

### Giai đoạn 3 — Giao diện tổng hợp và kiểm soát an toàn

- Màn hình chính gồm: chọn hồ sơ lớp, tháng/năm, thư mục nguồn, thư mục kết quả, nút `TỔNG HỢP`.
- Hiển thị tiến trình theo file; không đóng băng giao diện khi Word chuyển đổi `.doc`.
- Trang tóm tắt: số học sinh, giao dịch cộng/trừ, giao dịch trùng, giao dịch vượt trần và mục cần xác nhận.
- Nút mở thẳng file kết quả và thư mục sao lưu.

**Tiêu chí đạt:** giáo viên chạy được toàn bộ quy trình trong giao diện, không cần dòng lệnh.

### Giai đoạn 4 — Chuẩn hóa nguồn Word/Excel và quy tắc

- Word: quét toàn bộ `.doc`/`.docx`, nhận diện bảng có Họ tên – Lớp – Nội dung – Điểm đề nghị; chuyển `.doc` trên bản sao tạm bằng Word cài tại máy.
- Excel: giữ bộ đọc các mẫu đã có; thêm cơ chế chọn sheet/cột nguồn trong hồ sơ khi mẫu lớp khác khác tên sheet.
- Quy tắc: giáo viên có thể thêm/sửa/tắt quy tắc điểm trong giao diện, nhưng mọi thay đổi ghi lịch sử.
- Cơ chế chống trùng dùng: học sinh + ngày/sự kiện + nội dung chuẩn hóa + loại điểm; mọi bản bị loại vẫn xuất trong nhật ký.

**Tiêu chí đạt:** thay tên file hoặc thay tổ/bộ phận không làm hệ thống bỏ sót Word; giao dịch không được suy đoán đều xuất sang xác nhận.

### Giai đoạn 5 — Kiểm thử thực tế và phát hành

- Chạy đối chiếu thủ công ít nhất hai tháng / hai lớp; mỗi giao dịch kết quả phải truy được nguồn.
- Kiểm thử các lỗi: tệp Word cũ, file bị khóa, file OneDrive chưa tải xong, trùng tên, lớp sai, trùng giao dịch, vượt trần.
- Đóng gói một thư mục cài đặt hoặc một file chạy Windows, kèm hướng dẫn cho giáo viên.
- Tạo cơ chế sao lưu trước khi nâng cấp hồ sơ hoặc ghi đè kết quả cùng tên.

**Tiêu chí đạt:** một đồng nghiệp mới có thể tạo hồ sơ lớp và xuất kết quả thử nghiệm mà không cần hỗ trợ kỹ thuật.

## Kế hoạch kiểm thử tối thiểu

| Nội dung | Kết quả cần có |
| --- | --- |
| Bộ dữ liệu kiểm thử | Không thay đổi kết quả đã chấp nhận, trừ lỗi đã được xác nhận sửa. |
| Lớp thứ hai | Sĩ số và tên được lấy từ hồ sơ lớp mới, không lẫn với lớp khác. |
| Word có cột điểm đề nghị | Cộng đúng số điểm và ghi nguyên nội dung hoạt động. |
| Word `.doc` | File gốc không đổi; lỗi chuyển đổi xuất hiện rõ nếu Word không khả dụng. |
| Hai học sinh có tên gần giống | Không tự cộng nhầm; đưa vào xác nhận. |
| Giao dịch lặp | Chỉ áp dụng một lần, nhưng còn minh chứng trong nhật ký. |
| Điểm cộng vượt trần | Tổng áp dụng không vượt trần; khoản bị cắt có trạng thái rõ ràng. |

## Thứ tự ưu tiên đề nghị

1. Giai đoạn 0 và 1: làm lõi đa lớp, vẫn dùng giao diện hiện tại.
2. Giai đoạn 2: để đồng nghiệp tự tạo lớp mới.
3. Giai đoạn 3: hoàn thiện trải nghiệm cho giáo viên.
4. Giai đoạn 4 và 5: mở rộng nguồn, kiểm thử và đóng gói phát hành.

Không nên bắt đầu bằng đóng gói file cài đặt. Trước hết cần chứng minh lõi đa lớp khớp kết quả trên ít nhất hai lớp thực tế.

## Dữ liệu đầu vào khi dùng V2

Giáo viên chủ nhiệm chỉ cần đặt các file sẵn có của lớp vào cùng một thư mục nguồn: danh sách học sinh hoặc file đánh giá có danh sách chuẩn, file mẫu hạnh kiểm/rèn luyện, file Word cộng điểm và các Excel vi phạm/điểm gốc. Ứng dụng không yêu cầu đổi tên file theo một chuẩn cứng.

Trong lần tạo hồ sơ đầu tiên, giáo viên xác nhận đề xuất của máy. Các tháng sau chỉ việc chọn hồ sơ lớp và thư mục nguồn mới.

## Prompt sẵn sàng để tiếp tục

> Bắt đầu Giai đoạn tiếp theo của V2 đa lớp cho hệ thống hạnh kiểm chạy local. Không sửa file nguồn. Người dùng sẽ chọn một thư mục có toàn bộ file sẵn có của lớp; trước hết hãy tự phân loại file, đề xuất danh sách học sinh chuẩn và file mẫu đầu ra, rồi hiển thị để GVCN xác nhận. Sau khi tôi xác nhận, tạo hồ sơ lớp cục bộ và kiểm thử song song với một lớp khác. Không tự suy đoán điểm hoặc ghép tên mơ hồ; mọi dữ liệu chưa chắc phải vào CẦN GVCN XÁC NHẬN.
