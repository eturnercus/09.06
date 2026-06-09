"""Тесты проверки окружения и subprocess."""

import os
import unittest
from unittest.mock import patch

from watchalert.screen_capture import (
    _clean_subprocess_env,
    is_appimage,
    is_running_as_root,
)


class TestRuntime(unittest.TestCase):
    def test_clean_env_strips_appimage_vars(self) -> None:
        with patch.dict(
            os.environ,
            {"LD_LIBRARY_PATH": "/tmp/app", "APPIMAGE": "/a.AppImage", "HOME": "/home/u"},
            clear=False,
        ):
            env = _clean_subprocess_env()
        self.assertNotIn("LD_LIBRARY_PATH", env)
        self.assertNotIn("APPIMAGE", env)
        self.assertEqual(env["HOME"], "/home/u")

    @patch.dict(os.environ, {"APPIMAGE": "/x.AppImage"}, clear=False)
    def test_is_appimage(self) -> None:
        self.assertTrue(is_appimage())

    @patch("os.geteuid", return_value=0)
    def test_is_root(self, _uid: object) -> None:
        self.assertTrue(is_running_as_root())


if __name__ == "__main__":
    unittest.main()
