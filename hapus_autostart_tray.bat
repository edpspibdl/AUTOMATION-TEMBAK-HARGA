@echo off
title Hapus Autostart Service Tray
cd /d "%~dp0"

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Otomasi_Indogrosir_Tray.lnk"

echo ================================================================
echo    HAPUS AUTOSTART SERVICE TRAY DARI WINDOWS STARTUP
echo ================================================================
echo.

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo [SUKSES] Shortcut di Startup berhasil dihapus.
) else (
    echo [INFO] Shortcut tidak ditemukan di Startup.
)

echo.
pause

