@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "CF=%ProgramFiles(x86)%\cloudflared\cloudflared.exe"
if not exist "%CF%" set "CF=%ProgramFiles%\cloudflared\cloudflared.exe"
set "CFG=%USERPROFILE%\.cloudflared\person-ai.yml"
if not exist "%CF%" (
  echo cloudflared bulunamadi. Kurmak icin: winget install Cloudflare.cloudflared
  pause
  exit /b 1
)
if not exist "%CFG%" (
  echo Tunel ayari bulunamadi: %CFG%
  pause
  exit /b 1
)
echo Person AI, uzaktan erisim tuneliyle birlikte acilacak.
echo Giris Cloudflare Access ile korunuyor; sadece izin verilen e-postalar girebilir.
echo Bu pencereyi kapatinca hem uygulama hem uzaktan erisim kapanir.
echo.
start "" /b "%CF%" tunnel --no-autoupdate --loglevel warn --config "%CFG%" run
call "%~dp0baslat.bat" %*
