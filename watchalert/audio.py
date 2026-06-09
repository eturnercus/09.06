"""Воспроизведение звукового файла."""

from __future__ import annotations

import threading
from pathlib import Path

import pygame


class SoundPlayer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._initialized = False
        self._sound_path: str | None = None

    def _ensure_init(self) -> None:
        if not self._initialized:
            pygame.mixer.init()
            self._initialized = True

    def set_sound(self, path: str | None) -> None:
        with self._lock:
            self._sound_path = path

    def play(self) -> None:
        with self._lock:
            path = self._sound_path
        if not path:
            return
        sound_file = Path(path)
        if not sound_file.is_file():
            return

        def _play() -> None:
            try:
                self._ensure_init()
                pygame.mixer.music.load(str(sound_file))
                pygame.mixer.music.play()
            except pygame.error:
                pass

        threading.Thread(target=_play, daemon=True).start()
