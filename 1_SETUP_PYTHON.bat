@echo off
title 1 - Setup Python (Portable)
cd /d "%~dp0"
echo.
echo ============================================================
echo    STEP 1 : INSTALL PORTABLE PYTHON
echo ============================================================
echo    No administrator rights needed.
echo.
if exist "python-portable\python.exe" goto ALREADY
py -V >nul 2>&1
if %errorlevel%==0 goto HASPY
python -V >nul 2>&1
if %errorlevel%==0 goto HASPY
echo    Downloading portable Python...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "try {" ^
  "  [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "  $u='https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip';" ^
  "  Invoke-WebRequest -Uri $u -OutFile 'py.zip' -UseBasicParsing;" ^
  "  Expand-Archive -Path 'py.zip' -DestinationPath 'python-portable' -Force;" ^
  "  Remove-Item 'py.zip' -Force; Write-Host '    OK';" ^
  "} catch { Write-Host ('    FAILED: ' + $_.Exception.Message); exit 1 }"
if not exist "python-portable\python.exe" goto FAILED
echo.
echo    SUCCESS. Next: run  2_START_SERVER.bat
echo.
pause
exit /b
:ALREADY
echo    Already installed. Next: run  2_START_SERVER.bat
echo.
pause
exit /b
:HASPY
echo    Python already on this server. Skip this step.
echo    Next: run  2_START_SERVER.bat
echo.
pause
exit /b
:FAILED
echo.
echo    DOWNLOAD FAILED - no internet or firewall blocks python.org
echo    Manual method:
echo      1. Download on a PC with internet:
echo         https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
echo      2. Copy the zip into this folder
echo      3. Right click - Extract All
echo      4. Rename extracted folder to:  python-portable
echo.
pause
exit /b
