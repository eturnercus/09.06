"""Общие типы данных."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Region:
    x: int
    y: int
    width: int
    height: int

    def to_mss_dict(self) -> dict[str, int]:
        return {
            "left": self.x,
            "top": self.y,
            "width": self.width,
            "height": self.height,
        }
