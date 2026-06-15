"""Снимок экрана через XDG Desktop Portal (GNOME/KDE Wayland и др.)."""

from __future__ import annotations

import secrets
from pathlib import Path
from urllib.parse import unquote, urlparse

from jeepney import MessageType, new_method_call
from jeepney.bus_messages import MatchRule
from jeepney.io.blocking import open_dbus_connection
from jeepney.wrappers import Variant, unwrap_msg


def portal_available() -> bool:
    try:
        with open_dbus_connection() as conn:
            return bool(conn.unique_name)
    except Exception:
        return False


def portal_screenshot_path(timeout: float = 45.0) -> Path:
    """Нес интерактивный снимок всего экрана через org.freedesktop.portal."""
    token = f"watchalert_{secrets.token_hex(4)}"
    with open_dbus_connection() as conn:
        msg = new_method_call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Screenshot",
            "Screenshot",
            "sa{sv}",
            "",
            {
                "interactive": Variant("b", False),
                "modal": Variant("b", False),
                "handle_token": Variant("s", token),
            },
        )
        reply = unwrap_msg(conn.send_and_get_reply(msg, timeout=timeout))
        request_path = reply[0]

        rule = MatchRule(
            path=request_path,
            interface="org.freedesktop.portal.Request",
            member="Response",
        )
        with conn.filter(rule) as queue:
            response = conn.recv_until_filtered(queue, timeout=timeout)

        if response.header.message_type is not MessageType.signal:
            raise RuntimeError("ожидался сигнал portal Response")

        status = response.body[0]
        if status != 0:
            raise RuntimeError(f"portal отклонил запрос (код {status})")

        results = response.body[1]
        uri = results.get("uri")
        if hasattr(uri, "value"):
            uri = uri.value
        if not uri:
            raise RuntimeError("portal не вернул uri")

        parsed = urlparse(str(uri))
        return Path(unquote(parsed.path))
