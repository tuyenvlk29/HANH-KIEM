@echo off
chcp 65001 >nul
title ĐẨY TOÀN BỘ DỰ ÁN LÊN GITHUB - HANH-KIEM
color 1F

echo =====================================================================
echo       HỆ THỐNG TỰ ĐỘNG ĐẨY DỰ ÁN LÊN GITHUB: tuyenvlk29/HANH-KIEM
echo =====================================================================
echo.

set "PATH=C:\Users\BUI NGOC TUYEN\AppData\Local\Programs\gh;C:\Users\BUI NGOC TUYEN\AppData\Local\Programs\MinGit\cmd;%PATH%"

echo [1/3] Kiểm tra trạng thái đăng nhập GitHub...
gh auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ---------------------------------------------------------------------
    echo  Chưa đăng nhập GitHub! Cửa sổ trình duyệt sẽ tự động mở ra.
    echo  Thầy chỉ cần bấm "Authorize" để cấp quyền đẩy code lên kho lưu trữ.
    echo ---------------------------------------------------------------------
    echo.
    gh auth login -h github.com -p https -w
    if %errorlevel% neq 0 (
        echo.
        echo [!] Đăng nhập chưa thành công. Vui lòng thử lại.
        pause
        exit /b 1
    )
) else (
    echo [OK] Đã đăng nhập GitHub thành công!
)

echo.
echo [2/3] Thiết lập quyền Git qua GitHub CLI...
gh auth setup-git

echo.
echo [3/3] Đang đẩy toàn bộ dự án lên https://github.com/tuyenvlk29/HANH-KIEM ...
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo =====================================================================
    echo   [THÀNH CÔNG] TOÀN BỘ DỰ ÁN ĐÃ ĐƯỢC TẢI LÊN GITHUB THÀNH CÔNG!
    echo   Link kho lưu trữ: https://github.com/tuyenvlk29/HANH-KIEM
    echo =====================================================================
) else (
    echo.
    echo [!] Quá trình đẩy code gặp lỗi. Vui lòng kiểm tra lại kết nối mạng.
)

echo.
pause
