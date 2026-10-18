@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "APP_PY=%PROJECT_DIR%app\main.py"
set "LOCAL_PY=%LOCALAPPDATA%\TuyenBui\HeThongHanhKiem\Python312\python.exe"
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%LOCAL_PY%" (
  "%LOCAL_PY%" -c "import openpyxl, docx, xlrd" >nul 2>nul
  if not errorlevel 1 (
    "%LOCAL_PY%" "%APP_PY%"
    if errorlevel 1 pause
    exit /b %errorlevel%
  )
)

if exist "%CODEX_PY%" (
  "%CODEX_PY%" -c "import openpyxl, docx, xlrd" >nul 2>nul
  if not errorlevel 1 (
    "%CODEX_PY%" "%APP_PY%"
    if errorlevel 1 pause
    exit /b %errorlevel%
  )
)

call "%PROJECT_DIR%CAI_DAT_VA_CHAY.cmd"
exit /b %errorlevel%
