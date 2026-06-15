#!/usr/bin/env bash
# Упаковка расширения WatchAlert Tab для Chrome и Firefox -> artifacts/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXT="$ROOT/extension"
ART="$ROOT/artifacts"
STAGING="$ROOT/build/extension-staging"

rm -rf "$STAGING"
mkdir -p "$ART" "$STAGING/chrome" "$STAGING/firefox"

copy_tree() {
  local dest="$1"
  cp -r "$EXT"/* "$dest/"
  rm -f "$dest/manifest.firefox.json"
}

copy_tree "$STAGING/chrome"
copy_tree "$STAGING/firefox"
cp "$EXT/manifest.firefox.json" "$STAGING/firefox/manifest.json"

CHROME_ZIP="$ART/WatchAlert-Tab-chrome.zip"
FIREFOX_ZIP="$ART/WatchAlert-Tab-firefox.zip"

rm -f "$CHROME_ZIP" "$FIREFOX_ZIP"

(
  cd "$STAGING/chrome"
  zip -qr "$CHROME_ZIP" .
)

(
  cd "$STAGING/firefox"
  zip -qr "$FIREFOX_ZIP" .
)

echo "Chrome:  $CHROME_ZIP ($(du -h "$CHROME_ZIP" | cut -f1))"
echo "Firefox: $FIREFOX_ZIP ($(du -h "$FIREFOX_ZIP" | cut -f1))"
