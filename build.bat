@echo off
setlocal
cd /d "%~dp0"

echo === WatchAlert: сборка Windows .exe ===
python --version >nul 2>&1 || (
  echo Ошибка: Python не найден. Установите Python 3.10+ с python.org
  exit /b 1
)

python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

set WATCHALERT_ROOT=%CD%
if not exist artifacts mkdir artifacts

python -m PyInstaller build\watchalert.spec ^
  --distpath build\pyinstaller-dist ^
  --workpath build\pyinstaller-work ^
  --noconfirm
if errorlevel 1 exit /b 1

copy /Y build\pyinstaller-dist\WatchAlert.exe artifacts\WatchAlert-windows-x86_64.exe
echo.
echo Готово: artifacts\WatchAlert-windows-x86_64.exe
endlocal
