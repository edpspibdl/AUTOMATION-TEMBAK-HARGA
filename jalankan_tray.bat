@echo off
title Menjalankan Service Tray Otomasi Indogrosir
cd /d "%~dp0"

echo [INFO] Menjalankan Service Tray di latar belakang...
start "" pythonw tray_service.py

echo.
echo ================================================================
echo  Service Tray telah berjalan di latar belakang!
echo  Silakan cek ikon "IDG" di System Tray (pojok kanan bawah jam).
echo ================================================================
timeout /t 3 >nul

