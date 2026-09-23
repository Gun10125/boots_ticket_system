@echo off
title Check System - Find Server Address
cd /d "%~dp0"
echo.
echo ============================================================
echo    SYSTEM CHECK
echo ============================================================
echo.
if exist "python-portable\python.exe" (
    echo  [OK] Portable Python found:
    "python-portable\python.exe" -V
) else (
    echo  --- trying: py ---
    py -V
    echo  --- trying: python ---
    python -V
)
echo.
if exist "app\data\boots_helpdesk.db" (
    echo  [OK] Database file exists
) else (
    echo  Database not created yet - appears after first start
)
echo.
echo ============================================================
echo  THIS SERVER IP ADDRESS - give this to your team:
echo ============================================================
ipconfig | findstr /C:"IPv4"
echo.
echo  Staff open in browser:   http://THAT-IP:8080
echo.
echo ============================================================
echo  Firewall rule status:
echo ============================================================
netsh advfirewall firewall show rule name="Boots Helpdesk 8080" | findstr /C:"Rule Name" /C:"Enabled" /C:"LocalPort"
echo.
echo  If nothing appears above, run 4_AUTO_START_AND_FIREWALL.bat
echo  as administrator.
echo.
pause
