import unittest
from pathlib import Path
from unittest.mock import patch

from app import config


class SettingsResolutionTests(unittest.TestCase):
    @patch("app.config.Path.exists", autospec=True)
    def test_release_binary_is_preferred_when_present(self, exists):
        def fake_exists(self):
            return str(self).endswith("target/release/archer")

        exists.side_effect = fake_exists

        binary = config.default_archer_binary()

        self.assertEqual(
            binary,
            str(Path(__file__).resolve().parents[2] / "archer-starter" / "target" / "release" / "archer"),
        )

    @patch("app.config.Path.exists", autospec=True)
    def test_debug_binary_is_fallback_when_release_missing(self, exists):
        exists.return_value = False

        binary = config.default_archer_binary()

        self.assertEqual(
            binary,
            str(Path(__file__).resolve().parents[2] / "archer-starter" / "target" / "debug" / "archer"),
        )


if __name__ == "__main__":
    unittest.main()
