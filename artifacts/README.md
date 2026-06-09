# Собранные артефакты WatchAlert

| Файл | Платформа | Описание |
|------|-----------|----------|
| `WatchAlert-windows-x86_64.exe` | Windows 10+ | Один исполняемый файл, Python не нужен |
| `WatchAlert-x86_64.AppImage` | Linux x86_64 | AppImage, `chmod +x` и запуск |
| `WatchAlert-linux-x86_64` | Linux x86_64 | Один исполняемый файл без AppImage |

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

```bash
./build/build_all.sh
```
