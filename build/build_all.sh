#!/usr/bin/env bash
# Полная сборка: Linux one-file, AppImage, Windows .exe -> artifacts/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/build/build.sh"
if command -v wine >/dev/null 2>&1 || command -v wine64 >/dev/null 2>&1; then
  "$ROOT/build/build-windows.sh" || echo "Windows-сборка пропущена (ошибка Wine)"
else
  echo "Wine не найден — Windows .exe не собран"
fi
"$ROOT/build/build-extension.sh"
echo ""
echo "Артефакты:"
ls -lh "$ROOT/artifacts"/WatchAlert*
