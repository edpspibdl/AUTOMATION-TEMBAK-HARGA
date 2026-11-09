@echo off
title Pasang Autostart Service Tray
cd /d "%~dp0"

set "TARGET_VBS=%~dp0jalankan_tray.vbs"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Otomasi_Indogrosir_Tray.lnk"

echo ================================================================
echo    PASANG AUTOSTART SERVICE TRAY KE WINDOWS STARTUP
echo ================================================================
echo.
echo Menambahkan shortcut ke folder Startup agar service otomatis
echo berjalan di pojok kanan bawah saat komputer dinyalakan...
echo.

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%TARGET_VBS%\"'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Service Tray Otomasi Indogrosir'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUKSES] Service Tray berhasil didaftarkan ke Windows Startup!
    echo Shortcut: %SHORTCUT_PATH%
) else (
    echo [GAGAL] Gagal membuat shortcut di folder Startup.
)

echo.
pause

