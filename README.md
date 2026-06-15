# WatchAlert

Кроссплатформенный мониторинг областей экрана со звуковым сигналом при **устойчивых** изменениях.

Два варианта продукта:

| | **WatchAlert** (десктоп) | **WatchAlert Tab** (браузер) |
|---|--------------------------|------------------------------|
| Область | Любой экран / монитор | Вкладки Chrome, Edge, Firefox |
| ОС | Linux, Windows | Расширение в браузере |
| Фон | Работает всегда | Можно переключаться на другие вкладки |

**Актуальный релиз:** [v1.4.0](https://github.com/eturnercus/09.06/releases/tag/v1.4.0) — все пять файлов в одном релизе.

---

## Скачать (Releases)

Готовые сборки: **[github.com/eturnercus/09.06/releases](https://github.com/eturnercus/09.06/releases)**

| Файл | Назначение |
|------|------------|
| `WatchAlert-windows-x86_64.exe` | Windows 10+ (без Python) |
| `WatchAlert-x86_64.AppImage` | Linux AppImage |
| `WatchAlert-linux-x86_64` | Linux, один бинарник |
| `WatchAlert-Tab-chrome.zip` | Расширение Chrome / Edge / Brave |
| `WatchAlert-Tab-firefox.zip` | Расширение Firefox 121+ |

> Для Firefox берите **v1.4.0** или новее.

---

## Десктопное приложение

### Возможности

- Несколько независимых областей мониторинга
- Настраиваемая задержка перед сигналом (1–3600 сек)
- Любой звуковой файл (WAV, MP3, OGG, FLAC)
- Три уровня чувствительности: **сильная** (на любое), **средняя** (на часть), **слабая** (только смена картинки)
- Живое превью каждой области
- Автосохранение настроек в `~/.watchalert/config.json` (Windows: `%USERPROFILE%\.watchalert\`)

### Запуск из релиза

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

**Не запускайте через sudo.**

### Требования для сборки из исходников

- Python 3.10+
- Linux или Windows

На Linux:
```bash
sudo apt install python3-tk libsdl2-dev scrot
```

**Захват экрана на Linux** — приложение само подбирает рабочий способ:

| Среда | Способы (по порядку) |
|-------|----------------------|
| Wayland (GNOME/KDE) | XDG Portal, grim, spectacle, gnome-screenshot, Pillow XCB |
| X11 | Pillow XCB, mss xlib, scrot, maim, ImageMagick, ffmpeg |

Кнопка **«Проверить захват»** в настройках показывает, что работает у вас.  
Если не работает на Wayland: `sudo apt install grim scrot` или сессия **Ubuntu on Xorg**.  
Принудительно: `WATCHALERT_CAPTURE=pillow_x11 ./WatchAlert.AppImage`

### Установка и запуск из исходников

```bash
pip install -r requirements.txt
python -m watchalert.main
```

### Как пользоваться

1. Укажите **задержку** — сколько секунд изменение должно сохраняться до сигнала.
2. Выберите **звуковой файл** и нажмите «Тест».
3. **«Добавить область»** — на каждом мониторе появится снимок; выделите прямоугольник.
4. **«▶ Старт»** — мониторинг и превью для каждой области.
5. При устойчивом изменении — звуковой сигнал.

**Esc** — отмена выбора области.

### Принцип работы

Периодический захват области **в память** (без файлов на диске), сравнение с эталонным кадром. При устойчивом отличии — таймер; по истечении задержки — звук и обновление эталона.

### Пересборка десктопа

```bash
./build/build.sh           # Linux binary + AppImage → artifacts/
./build/build_all.sh       # десктоп + zip расширений
```

Windows: `build.bat`

### Тесты

```bash
pip install -r requirements.txt pytest
python -m pytest tests/ -q
```

---

## Расширение для браузера (WatchAlert Tab)

Тот же принцип мониторинга, но зоны на **вкладках** браузера. Поддерживаются **Chrome, Edge и Firefox**.

Подробная инструкция: [extension/README.md](extension/README.md)

### Установка

**Chrome / Edge**
1. Скачайте `WatchAlert-Tab-chrome.zip` из [Releases](https://github.com/eturnercus/09.06/releases)
2. Распакуйте в папку
3. `chrome://extensions/` → режим разработчика → «Загрузить распакованное»

**Firefox**
1. Скачайте `WatchAlert-Tab-firefox.zip`
2. Распакуйте в папку
3. `about:debugging` → «Этот Firefox» → «Загрузить временное дополнение…» → выберите `manifest.json`

### Кратко: как пользоваться

1. **«+ Текущая»** — добавить вкладку
2. **«+ Зона»** — выделить область на странице
3. **«▶ Старт»** — мониторинг в фоне
4. (Опционально) **«Закрепить окно»** — только вкладки из выбранного окна

Звук: кнопка «Выбрать файл…» открывает отдельную вкладку (popup не закрывается при выборе файла).

### Сборка zip расширений

```bash
./build/build-extension.sh
./build/validate-extension.sh   # проверка перед релизом
```

---

## CI / релизы

Тег `v*` на `main` запускает GitHub Actions: сборка Linux, Windows, AppImage и zip расширений → один [Release](https://github.com/eturnercus/09.06/releases) со всеми артефактами.

---

## Лицензия и автор

by eturnercus
