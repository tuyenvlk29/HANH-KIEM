@echo off
setlocal EnableExtensions
set "PROJECT_DIR=%~dp0"
set "INSTALLER=%PROJECT_DIR%installer\python-3.12.10-amd64.exe"
set "WHEELS=%PROJECT_DIR%installer\wheels"
set "RUNTIME_DIR=%LOCALAPPDATA%\TuyenBui\HeThongHanhKiem\Python312"
set "APP_PY=%RUNTIME_DIR%\python.exe"

if not exist "%INSTALLER%" (
  echo Khong tim thay file cai dat Python trong goi.
  echo Hay giai nen day du toan bo goi truoc khi chay.
  pause
  exit /b 1
)

if not exist "%APP_PY%" (
  echo.
  echo He thong can cai Python cuc bo de chay ung dung nay.
  echo Python se duoc cai rieng cho tai khoan Windows hien tai tai:
  echo %RUNTIME_DIR%
  echo Khong thay doi Python cua ung dung khac va khong tai du lieu hoc sinh len Internet.
  choice /C YN /M "Cho phep cai dat va tiep tuc"
  if errorlevel 2 exit /b 0
  "%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=0 Include_pip=1 Include_test=0 TargetDir="%RUNTIME_DIR%"
  if errorlevel 1 (
    echo Cai dat Python khong thanh cong. Hay thu chay lai voi quyen tai khoan Windows hien tai.
    pause
    exit /b 1
  )
)

echo Dang chuan bi cac thu vien can thiet...
"%APP_PY%" -m pip install --disable-pip-version-check --no-index --find-links "%WHEELS%" --upgrade openpyxl==3.1.5 python-docx==1.1.2 xlrd==2.0.1
if errorlevel 1 (
  echo Khong the cai cac thu vien trong goi.
  pause
  exit /b 1
)

start "He thong hanh kiem" /wait "%APP_PY%" "%PROJECT_DIR%app\main.py"
exit /b %errorlevel%
