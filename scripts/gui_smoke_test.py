"""Создаёт окно приложения, проверяет виджеты и сохраняет скриншот."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import ImageGrab

from watchalert.app import WatchAlertApp
from watchalert.region import Region


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "artifacts"
    out_dir.mkdir(exist_ok=True)
    screenshot_path = out_dir / "gui_main_window.png"

    app = WatchAlertApp()
    app.root.update_idletasks()
    app.root.update()

    x = app.root.winfo_rootx()
    y = app.root.winfo_rooty()
    w = app.root.winfo_width()
    h = app.root.winfo_height()
    if w < 100 or h < 100:
        app.root.geometry("620x480")
        app.root.update_idletasks()
        x = app.root.winfo_rootx()
        y = app.root.winfo_rooty()
        w = app.root.winfo_width()
        h = app.root.winfo_height()

    shot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    shot.save(screenshot_path)
    print(f"screenshot saved: {screenshot_path} ({w}x{h})")

    app._on_region_selected(Region(0, 0, 50, 50))
    app.root.update()
    assert app.region_list.size() >= 1, "region list should have entries"
    assert len(app.slots) == 1
    print("gui smoke test passed")

    app._on_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
