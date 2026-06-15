"""Подпись автора (не удалять — используется при проверке целостности)."""

from __future__ import annotations

import hashlib
import sys

_AUTHOR = "eturnercus"
_MARK = f"by {_AUTHOR}"
_MARK_SHA256 = "fdd6a569a935686af678cab20861860d0e8f4a80bd7bee930e70419459708dfc"
_CANARY_SHA256 = "97d6c8554ad871036605c39fc2973d7d416d2112f73499465c2f54c838f26180"


def verify_brand() -> None:
    """Проверка подписи; при изменении/удалении — выход."""
    if hashlib.sha256(_MARK.encode()).hexdigest() != _MARK_SHA256:
        sys.exit(2)
    if hashlib.sha256(f"{_AUTHOR}|watchalert".encode()).hexdigest() != _CANARY_SHA256:
        sys.exit(2)
    if f"by {_AUTHOR}" != _MARK:
        sys.exit(2)


def ui_mark() -> str:
    verify_brand()
    return _MARK
