"""Три уровня чувствительности (десктоп)."""

from __future__ import annotations

from typing import TypedDict


class SensitivityConfig(TypedDict):
    threshold: float
    min_changed_ratio: float
    label: str


LEVELS: dict[str, SensitivityConfig] = {
    "high": {
        "threshold": 3.0,
        "min_changed_ratio": 0.0,
        "label": "Сильная",
    },
    "medium": {
        "threshold": 10.0,
        "min_changed_ratio": 0.06,
        "label": "Средняя",
    },
    "low": {
        "threshold": 24.0,
        "min_changed_ratio": 0.15,
        "label": "Слабая",
    },
}


def normalize_sensitivity(value: object) -> str:
    if value in LEVELS:
        return str(value)
    if isinstance(value, (int, float)):
        n = float(value)
        if n <= 5:
            return "high"
        if n <= 14:
            return "medium"
        return "low"
    return "medium"


def get_sensitivity_config(value: object) -> SensitivityConfig:
    return LEVELS[normalize_sensitivity(value)]
