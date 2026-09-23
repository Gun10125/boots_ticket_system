@echo off
title 4 - Auto Start And Open Firewall
cd /d "%~dp0"
net session >nul 2>&1
if not %errorlevel%==0 (
    echo.
    echo    Please RIGHT CLICK this file and choose
    echo    "Run as administrator"
    echo.
    pause
    exit /b
)
echo.
echo ============================================================
echo    AUTO START + ALLOW CLIENT PCs TO CONNECT
echo ============================================================
echo      1. Starts the system automatically when server boots
echo      2. Opens Windows Firewall port 8080 for other PCs
echo.
echo    [1] Install
echo    [2] Remove
echo    [3] Cancel
echo.
set /p "OPT=Choose 1, 2 or 3: "
if "%OPT%"=="2" goto REMOVE
if "%OPT%"=="1" goto INSTALL
goto END
:INSTALL
schtasks /Create /TN "BootsHelpdesk" /TR "\"%~dp02_START_SERVER.bat\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F
netsh advfirewall firewall delete rule name="Boots Helpdesk 8080" >nul 2>&1
netsh advfirewall firewall add rule name="Boots Helpdesk 8080" dir=in action=allow protocol=TCP localport=8080 profile=any
echo.
echo    DONE. Client PCs can now connect.
echo.
pause
exit /b
:REMOVE
schtasks /Delete /TN "BootsHelpdesk" /F
netsh advfirewall firewall delete rule name="Boots Helpdesk 8080" >nul 2>&1
echo    Removed.
pause
exit /b
:END
echo Cancelled.
pause
