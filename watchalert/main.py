"""Точка входа WatchAlert."""

from watchalert.app import WatchAlertApp
from watchalert.runtime_check import check_runtime_or_exit, preserve_user_display_env


def main() -> None:
    preserve_user_display_env()
    check_runtime_or_exit()
    WatchAlertApp().run()


if __name__ == "__main__":
    main()
