# Собранные артефакты WatchAlert

| Файл | Платформа | Описание |
|------|-----------|----------|
| `WatchAlert-windows-x86_64.exe` | Windows 10+ | Один исполняемый файл, Python не нужен |
| `WatchAlert-x86_64.AppImage` | Linux x86_64 | AppImage, `chmod +x` и запуск |
| `WatchAlert-linux-x86_64` | Linux x86_64 | Один исполняемый файл без AppImage |
| `WatchAlert-Tab-chrome.zip` | Chrome / Edge | Расширение для вкладок (распаковать → загрузить unpacked) |
| `WatchAlert-Tab-firefox.zip` | Firefox 109+ | То же расширение для Firefox |

## Запуск

**Windows:** двойной клик по `WatchAlert-windows-x86_64.exe`

**Linux AppImage:**
```bash
chmod +x WatchAlert-x86_64.AppImage
./WatchAlert-x86_64.AppImage
```

**Linux binary:**
```bash
chmod +x WatchAlert-linux-x86_64
./WatchAlert-linux-x86_64
```

Настройки сохраняются в `~/.watchalert/config.json` (на Windows: `%USERPROFILE%\.watchalert\`).

## Пересборка

**Linux:**
```bash
./build/build_all.sh          # десктоп + zip расширений
./build/build-extension.sh    # только Chrome/Firefox zip
```

**Windows:**
```bat
build.bat
```
