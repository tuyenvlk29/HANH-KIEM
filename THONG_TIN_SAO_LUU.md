# Bản sao lưu dự án

## Nội dung được lưu

- Mã ứng dụng trong `app/`.
- Lệnh chạy, lệnh cài đặt Python và các lệnh kiểm tra trong `commands/`.
- Python 3.12.10, các thư viện cài đặt offline trong `installer/`.
- Toàn bộ kế hoạch, lộ trình và prompt: `LO_TRINH_V2_DA_LOP.md`, `PROMPT_TIEP_TUC.md`, `PROJECT_CONTEXT.md`.
- Hướng dẫn, cấu hình, bộ kiểm thử và các gói phát hành đã tạo.
- File nguồn gốc không thay đổi trong `sources_original/` và bản làm việc trong `work/`.
- Các file kết quả và gói phát hành trong `outputs/`.

## Vị trí bản sao lưu

Các bản sao lưu đầy đủ được đặt trong thư mục `backups/` ngay trong dự án. Bản sao lưu không bao gồm `node_modules/` vì đây là thư mục phụ thuộc môi trường phát triển, có thể tạo lại và không chứa dữ liệu nghiệp vụ của hệ thống.

## Tạo bản sao lưu mới

Nhấp phải hoặc chạy trong PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\commands\TAO_SAO_LUU_DU_AN.ps1
```

Không mở, sửa hay di chuyển file trong `sources_original/` nếu chưa có bản sao dự phòng.
