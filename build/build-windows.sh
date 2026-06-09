#!/usr/bin/env bash
# Сборка Windows .exe через Wine + полный Python с tkinter.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="$ROOT/artifacts"
WIN_PY="$ROOT/build/win-python"
PY_INSTALLER="$ROOT/build/python-3.12.7-amd64.exe"
PY_VER="3.12.7"

cd "$ROOT"
mkdir -p "$ARTIFACTS"

if ! command -v wine64 >/dev/null 2>&1 && ! command -v wine >/dev/null 2>&1; then
  echo "Wine не установлен — пропуск Windows-сборки"
  exit 1
fi

WINE="$(command -v wine64 || command -v wine)"
WIN_PATH() { echo "$1" | sed 's/\//\\/g'; }

if [[ ! -f "$WIN_PY/python.exe" ]]; then
  echo "==> Установка Python $PY_VER для Windows (с tkinter)"
  if [[ ! -f "$PY_INSTALLER" ]]; then
    wget -q -O "$PY_INSTALLER" \
      "https://www.python.org/ftp/python/${PY_VER}/python-${PY_VER}-amd64.exe"
  fi
  rm -rf "$WIN_PY"
  mkdir -p "$WIN_PY"
  WINEDEBUG=-all "$WINE" "$PY_INSTALLER" /quiet InstallAllUsers=0 \
    Include_pip=1 Include_tcltk=1 Include_test=0 Shortcuts=0 \
    "TargetDir=Z:$(WIN_PATH "$WIN_PY")"
fi

PY="$WIN_PY/python.exe"
if [[ ! -f "$PY" ]]; then
  echo "Ошибка: python.exe не найден после установки"
  exit 1
fi

echo "==> Проверка tkinter"
WINEDEBUG=-all "$WINE" "$PY" -c "import tkinter; print('tkinter ok')"

echo "==> Установка зависимостей"
WINEDEBUG=-all "$WINE" "$PY" -m pip install -q pyinstaller mss Pillow pygame

echo "==> PyInstaller one-file (Windows)"
export WATCHALERT_ROOT="$ROOT"
rm -rf "$ROOT/build/pyinstaller-win-dist" "$ROOT/build/pyinstaller-win-work"
WINEDEBUG=-all "$WINE" "$PY" -m PyInstaller "$ROOT/build/watchalert.spec" \
  --distpath "Z:$(WIN_PATH "$ROOT/build/pyinstaller-win-dist")" \
  --workpath "Z:$(WIN_PATH "$ROOT/build/pyinstaller-win-work")" \
  --noconfirm

cp -f "$ROOT/build/pyinstaller-win-dist/WatchAlert.exe" "$ARTIFACTS/WatchAlert-windows-x86_64.exe"
echo "    -> artifacts/WatchAlert-windows-x86_64.exe"
ls -lh "$ARTIFACTS/WatchAlert-windows-x86_64.exe"
