@echo off
title 9 - Repair Database
cd /d "%~dp0"
echo.
echo ============================================================
echo    REPAIR DATABASE
echo ============================================================
echo.
echo    Use this ONLY if the server shows a database error
echo    such as:  no such column
echo.
echo    This renames the current database to a backup file,
echo    so the system can build a fresh one.
echo    Your old file is NOT deleted.
echo.
if not exist "app\data\boots_helpdesk.db" (
    echo    No database file found. Nothing to repair.
    echo.
    pause
    exit /b
)
set /p "OK=Type YES and press Enter to continue: "
if /I not "%OK%"=="YES" goto CANCEL
set "STAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%"
set "STAMP=%STAMP: =0%"
ren "app\data\boots_helpdesk.db" "boots_helpdesk_backup_%STAMP%.db"
if exist "app\data\boots_helpdesk.db-wal" del "app\data\boots_helpdesk.db-wal"
if exist "app\data\boots_helpdesk.db-shm" del "app\data\boots_helpdesk.db-shm"
echo.
echo    DONE. Old database saved as:
echo       boots_helpdesk_backup_%STAMP%.db
echo.
echo    Next steps:
echo       1. Run 2_START_SERVER.bat
echo       2. Run 3_IMPORT_OLD_DATA.bat to load your Excel again
echo.
pause
exit /b
:CANCEL
echo Cancelled.
pause
