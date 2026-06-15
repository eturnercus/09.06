"""Точка входа WatchAlert."""

from watchalert.app import WatchAlertApp
from watchalert.brand import verify_brand
from watchalert.runtime_check import check_runtime_or_exit, preserve_user_display_env
from watchalert.screen_capture import ensure_probed


def main() -> None:
    preserve_user_display_env()
    check_runtime_or_exit()
    verify_brand()
    ensure_probed()
    WatchAlertApp().run()


if __name__ == "__main__":
    main()
