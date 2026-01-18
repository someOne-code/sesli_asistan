@echo off
title Melody Sesli Asistan - INTERACTIVE MODE
color 0A
cls

echo ============================================================
echo     MELODY SESLI ASISTAN - BASLATILIYOR...
echo ============================================================
echo.

cd /d "%~dp0"

REM Virtual environment aktivasyonu
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [!] UYARI: venv bulunamadi! Python global kullanilacak.
)

echo.
echo [+] Asistan ve Veritabani hazirlaniyor...
echo [+] Sohbet baslasin!
echo.
echo ============================================================
echo.

python scripts/interactive_mode.py

echo.
echo ============================================================
echo Melody kapandi.
pause
