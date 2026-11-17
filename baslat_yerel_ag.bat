@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Person AI yerel agdaki diger cihazlara acilacak.
echo Bu secenegi yalnizca guvendigin bir agda kullan.
echo.
call "%~dp0baslat.bat" --host 0.0.0.0 %*
