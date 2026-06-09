#!/usr/bin/env bash
# Сборка Linux one-file бинарника и AppImage в artifacts/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="$ROOT/artifacts"
BUILD="$ROOT/build"
APPDIR="$BUILD/WatchAlert.AppDir"
PYINSTALLER="$HOME/.local/bin/pyinstaller"
APPIMAGETOOL="$BUILD/appimagetool-x86_64.AppImage"

cd "$ROOT"
mkdir -p "$ARTIFACTS" "$BUILD"

export PATH="$HOME/.local/bin:$PATH"
export WATCHALERT_ROOT="$ROOT"

echo "==> PyInstaller one-file (Linux)"
rm -rf "$BUILD/pyinstaller-dist" "$BUILD/pyinstaller-work"
"$PYINSTALLER" "$BUILD/watchalert.spec" \
  --distpath "$BUILD/pyinstaller-dist" \
  --workpath "$BUILD/pyinstaller-work" \
  --noconfirm

LINUX_BIN="$BUILD/pyinstaller-dist/WatchAlert"
cp -f "$LINUX_BIN" "$ARTIFACTS/WatchAlert-linux-x86_64"
chmod +x "$ARTIFACTS/WatchAlert-linux-x86_64"
echo "    -> artifacts/WatchAlert-linux-x86_64"

echo "==> AppImage"
if [[ ! -x "$APPIMAGETOOL" ]]; then
  wget -q -O "$APPIMAGETOOL" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -f "$LINUX_BIN" "$APPDIR/usr/bin/WatchAlert"
chmod +x "$APPDIR/usr/bin/WatchAlert"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/WatchAlert" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/watchalert.desktop" <<'EOF'
[Desktop Entry]
Name=WatchAlert
Comment=Мониторинг областей экрана со звуковым сигналом
Exec=WatchAlert
Icon=watchalert
Type=Application
Categories=Utility;
EOF
cp "$APPDIR/watchalert.desktop" "$APPDIR/usr/share/applications/"

# Простая иконка 256x256 (PNG)
python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw

paths = [
    Path("build/WatchAlert.AppDir/usr/share/icons/hicolor/256x256/apps/watchalert.png"),
    Path("build/WatchAlert.AppDir/watchalert.png"),
]
img = Image.new("RGBA", (256, 256), (45, 52, 64, 255))
d = ImageDraw.Draw(img)
d.rounded_rectangle((32, 32, 224, 224), radius=28, fill=(0, 200, 120, 255))
d.ellipse((88, 88, 168, 168), fill=(255, 255, 255, 230))
for out in paths:
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
PY

export ARCH=x86_64
OUTPUT="$ARTIFACTS/WatchAlert-x86_64.AppImage"
rm -f "$OUTPUT"
"$APPIMAGETOOL" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"
echo "    -> artifacts/WatchAlert-x86_64.AppImage"

echo "==> Готово"
ls -lh "$ARTIFACTS"/WatchAlert*
