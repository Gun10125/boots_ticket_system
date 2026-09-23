@echo off
title BOOTS IT HELPDESK - SERVER
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
echo.
echo    Python not found. Run  1_SETUP_PYTHON.bat  first.
echo.
pause
exit /b
:FOUND
cd /d "%~dp0app"
echo.
echo ============================================================
echo    BOOTS IT HELPDESK - SERVER IS STARTING
echo ============================================================
echo    Keep this window OPEN while staff are using the system.
echo    To stop: press Ctrl + C
echo ============================================================
echo.
"%PY%" server.py 8080
echo.
echo Server stopped.
pause
