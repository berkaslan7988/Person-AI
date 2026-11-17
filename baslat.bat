@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Person AI
where python >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org adresinden kurup tekrar dene.
  pause
  exit /b 1
)
python server.py %*
pause
