@echo off
title 3 - Import Old Data From Excel
cd /d "%~dp0"
set "PY="
if exist "python-portable\python.exe" (
    set "PY=%~dp0python-portable\python.exe"
    goto FOUND
)
py -V >nul 2>&1
if %errorlevel%==0 ( set "PY=py" & goto FOUND )
python -V >nul 2>&1
if %errorlevel%==0 ( set "PY=python" & goto FOUND )
echo Python not found. Run 1_SETUP_PYTHON.bat first.
pause
exit /b
:FOUND
cd /d "%~dp0app"
echo.
echo ============================================================
echo    IMPORT OLD TICKETS FROM EXCEL
echo ============================================================
echo.
echo    Drag your Excel file into this window, then press Enter.
echo    Duplicates are skipped - safe to run again.
echo.
set /p "XLS=Excel file: "
echo.
"%PY%" import_excel.py %XLS%
