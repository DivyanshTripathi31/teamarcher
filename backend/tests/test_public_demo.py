from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from app import main, security


class Query:
    def __init__(self, user):
        self.user = user

    def filter(self, *_args):
        return self

    def first(self):
        return self.user


class Database:
    def __init__(self, user):
        self.user = user

    def query(self, _model):
        return Query(self.user)


class PublicDemoTests(TestCase):
    settings = SimpleNamespace(
        jwt_secret="test-secret",
        jwt_expire_minutes=480,
        public_demo_mode=True,
        public_demo_upload_code="shared-demo-code",
        public_demo_upload_username="Demo Uploader",
        public_demo_upload_grant_minutes=20,
    )

    def test_code_is_verified_server_side_and_returns_only_a_short_lived_grant(self):
        user = SimpleNamespace(id=7, role="ADMIN")
        with patch("app.main.settings", self.settings), patch("app.security.get_settings", return_value=self.settings):
            result = main.public_demo_upload_access(main.PublicDemoUploadCode(code="shared-demo-code"), Database(user))
            self.assertIn("access_token", result)
            self.assertNotIn("shared-demo-code", result.values())
            self.assertEqual(security.demo_upload_subject(SimpleNamespace(credentials=result["access_token"])), 7)

    def test_incorrect_code_never_returns_a_grant(self):
        with patch("app.main.settings", self.settings), patch("app.security.get_settings", return_value=self.settings):
            with self.assertRaises(HTTPException) as raised:
                main.public_demo_upload_access(main.PublicDemoUploadCode(code="incorrect"), Database(SimpleNamespace(id=7, role="ADMIN")))
        self.assertEqual(raised.exception.status_code, 401)

    def test_demo_grant_cannot_be_used_as_a_normal_login_session(self):
        with patch("app.security.get_settings", return_value=self.settings):
            token = security.create_demo_upload_grant(7)
            with self.assertRaises(HTTPException):
                security.token_subject(SimpleNamespace(credentials=token))

