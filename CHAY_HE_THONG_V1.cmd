@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "CODEX_PY=C:\Users\BUI NGOC TUYEN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%CODEX_PY%" (
  "%CODEX_PY%" "%PROJECT_DIR%app\main.py"
  if errorlevel 1 pause
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py "%PROJECT_DIR%app\main.py"
  if errorlevel 1 pause
  exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "%PROJECT_DIR%app\main.py"
  if errorlevel 1 pause
  exit /b %errorlevel%
)

echo Khong tim thay Python de chay he thong.
pause
exit /b 1
