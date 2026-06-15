#!/usr/bin/env bash
# Проверка расширения WatchAlert Tab (Chrome + Firefox) перед релизом.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXT="$ROOT/extension"
ART="$ROOT/artifacts"
STAGING="$ROOT/build/extension-staging/firefox"
FAIL=0

red() { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }

check() {
  local name="$1"
  shift
  if "$@"; then
    green "OK  $name"
  else
    red "FAIL  $name"
    FAIL=1
  fi
}

echo "=== WatchAlert extension validation ==="

./build/build-extension.sh >/dev/null

check "Firefox zip exists" test -f "$ART/WatchAlert-Tab-firefox.zip"
check "Chrome zip exists" test -f "$ART/WatchAlert-Tab-chrome.zip"

check "Firefox manifest.json valid" python3 -c "
import json, zipfile
with zipfile.ZipFile('$ART/WatchAlert-Tab-firefox.zip') as z:
    m = json.loads(z.read('manifest.json'))
assert m['manifest_version'] == 3
assert m['background']['type'] == 'module'
assert 'scripts' in m['background'], 'Firefox needs background.scripts'
assert 'service_worker' not in m['background'], 'Firefox must not use service_worker'
assert 'notifications' in m['permissions']
"

check "Firefox manifest has gecko id" python3 -c "
import json, zipfile
with zipfile.ZipFile('$ART/WatchAlert-Tab-firefox.zip') as z:
    m = json.loads(z.read('manifest.json'))
assert 'browser_specific_settings' in m
"

check "Chrome manifest.json valid" python3 -c "
import json, zipfile
with zipfile.ZipFile('$ART/WatchAlert-Tab-chrome.zip') as z:
    m = json.loads(z.read('manifest.json'))
assert m['manifest_version'] == 3
assert m['background']['type'] == 'module'
assert 'service_worker' in m['background'], 'Chrome needs background.service_worker'
assert 'scripts' not in m['background'], 'Chrome must not use background.scripts'
assert 'tabCapture' in m['permissions']
assert 'offscreen' in m['permissions']
assert 'browser_specific_settings' not in m
"

CHROME_REQUIRED=(
  manifest.json
  background/service-worker.js
  offscreen/offscreen.html
  offscreen/offscreen.js
  content/zone-selector.js
  popup/popup.html
  popup/popup.js
)

for path in "${CHROME_REQUIRED[@]}"; do
  if unzip -Z1 "$ART/WatchAlert-Tab-chrome.zip" | grep -qxF "$path"; then
    green "OK  chrome zip contains $path"
  else
    red "FAIL  chrome zip contains $path"
    FAIL=1
  fi
done

check "offscreen sends OFFSCREEN_READY" grep -q OFFSCREEN_READY "$EXT/offscreen/offscreen.js"
check "service-worker handles OFFSCREEN_READY" grep -q OFFSCREEN_READY "$EXT/background/service-worker.js"

CRITICAL_MODULES=(
  background/service-worker.js
  background/firefox-sync.js
  shared/brand.js
  shared/browser.js
  shared/constants.js
  shared/diff.js
  shared/storage.js
  shared/play-alarm.js
  shared/platform.js
  shared/window-pin.js
)

MOCK_BROWSER='
const L = { addListener() {} };
const asyncObj = () => ({});
globalThis.chrome = {
  runtime: {
    onMessage: L,
    onStartup: L,
    onInstalled: L,
    getURL: (p) => p,
    sendMessage: async () => ({}),
    getContexts: async () => [],
  },
  tabs: {
    onRemoved: L,
    onUpdated: L,
    query: async () => [],
    get: async () => ({ id: 1, status: "complete" }),
    update: async () => ({}),
    sendMessage: async () => ({}),
    create: async () => ({ id: 1 }),
    remove: async () => ({}),
    captureTab: async () => "data:image/png;base64,",
  },
  storage: {
    local: { get: async () => ({}), set: async () => {} },
    onChanged: L,
    session: {
      get: async () => ({}),
      set: async () => {},
      onChanged: L,
    },
  },
  action: { setBadgeText() {}, setBadgeBackgroundColor() {} },
  windows: {
    onRemoved: L,
    get: async () => ({ id: 1, tabs: [] }),
    getAll: async () => [],
  },
  scripting: { executeScript: async () => [] },
  notifications: { create: async () => "" },
  offscreen: { createDocument: async () => {}, closeDocument: async () => {} },
};
'

for rel in "${CRITICAL_MODULES[@]}"; do
  if ! node --input-type=module --eval "$MOCK_BROWSER; await import('file://$EXT/$rel');" 2>/dev/null; then
    red "FAIL  ES module import: $rel"
    node --input-type=module --eval "$MOCK_BROWSER; await import('file://$EXT/$rel');" 2>&1 | head -8
    FAIL=1
  else
    green "OK  ES module import: $rel"
  fi
done

# UI-скрипты: полная проверка ESM (с моком DOM для страниц)
MOCK_DOM='
globalThis.document = {
  getElementById: (id) => ({
    id,
    textContent: "",
    set src(v) {},
    play: async () => {},
  }),
};
'

for rel in pages/ff-monitor.js pages/sound-picker.js; do
  if ! node --input-type=module --eval "$MOCK_BROWSER; $MOCK_DOM; await import('file://$EXT/$rel');" 2>/dev/null; then
    red "FAIL  ES module import: $rel"
    node --input-type=module --eval "$MOCK_BROWSER; $MOCK_DOM; await import('file://$EXT/$rel');" 2>&1 | head -8
    FAIL=1
  else
    green "OK  ES module import: $rel"
  fi
done

for rel in popup/popup.js; do
  if node --check "$EXT/$rel" 2>/dev/null; then
    green "OK  syntax: $rel"
  else
    red "FAIL  syntax: $rel"
    node --check "$EXT/$rel" 2>&1 | head -5
    FAIL=1
  fi
done

check "service-worker defines OFFSCREEN_URL" grep -q 'const OFFSCREEN_URL' "$EXT/background/service-worker.js"
check "service-worker has FF_CAPTURE_TAB" grep -q 'FF_CAPTURE_TAB' "$EXT/background/service-worker.js"
check "ff-monitor listens storage.session.onChanged" grep -q 'storage.session.onChanged' "$EXT/pages/ff-monitor.js"
check "firefox-sync uses storage.session" grep -q 'storage.session' "$EXT/background/firefox-sync.js"
check "brand mark length check" node --input-type=module -e "import { assertBrand } from './extension/shared/brand.js'; assertBrand();"

# Обязательные файлы в firefox zip
REQUIRED=(
  manifest.json
  background/service-worker.js
  background/firefox-sync.js
  pages/ff-monitor.html
  pages/ff-monitor.js
  shared/brand.js
  shared/browser.js
  shared/diff.js
  content/zone-selector.js
  popup/popup.html
  popup/popup.js
  icons/icon48.png
)

for path in "${REQUIRED[@]}"; do
  if unzip -Z1 "$ART/WatchAlert-Tab-firefox.zip" | grep -qxF "$path"; then
    green "OK  zip contains $path"
  else
    red "FAIL  zip contains $path"
    FAIL=1
  fi
done

if [[ "$FAIL" -eq 0 ]]; then
  green "=== All checks passed ==="
else
  red "=== Validation failed ==="
  exit 1
fi
