from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from app import main, security


class PublicDemoTests(TestCase):
    settings = SimpleNamespace(
        jwt_secret="test-secret",
        jwt_expire_minutes=480,
        public_demo_mode=True,
        public_demo_upload_code="shared-demo-code",
        public_demo_upload_grant_minutes=20,
    )

    def test_code_is_verified_server_side_and_returns_only_a_short_lived_grant(self):
        with patch("app.main.settings", self.settings), patch("app.security.get_settings", return_value=self.settings):
            result = main.public_demo_upload_access(main.PublicDemoUploadCode(code="shared-demo-code"))
            self.assertIn("access_token", result)
            self.assertNotIn("shared-demo-code", result.values())
            self.assertIsNone(security.verify_demo_upload_grant(SimpleNamespace(credentials=result["access_token"])))

    def test_incorrect_code_never_returns_a_grant(self):
        with patch("app.main.settings", self.settings), patch("app.security.get_settings", return_value=self.settings):
            with self.assertRaises(HTTPException) as raised:
                main.public_demo_upload_access(main.PublicDemoUploadCode(code="incorrect"))
        self.assertEqual(raised.exception.status_code, 401)

    def test_demo_grant_cannot_be_used_as_a_normal_login_session(self):
        with patch("app.security.get_settings", return_value=self.settings):
            token = security.create_demo_upload_grant()
            with self.assertRaises(HTTPException):
                security.token_subject(SimpleNamespace(credentials=token))
