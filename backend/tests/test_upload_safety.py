import asyncio
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from app import main


class Query:
    def __init__(self, existing=None):
        self.existing = existing

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self.existing


class Database:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    def query(self, _model):
        return Query(self.existing)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        if self.added:
            self.added[0].id = 1

    def commit(self):
        pass

    def refresh(self, _value):
        pass


def file(name, contents=b"test", content_type="application/octet-stream"):
    return UploadFile(filename=name, file=BytesIO(contents), headers={"content-type": content_type})


class UploadSafetyTests(TestCase):
    user = SimpleNamespace(id=1, role="ADMIN", must_change_password=False)

    def create(self, files, db):
        return asyncio.run(
            main.create_presentation(
                title="Verification",
                version="V1",
                presentation_date=date.today(),
                authors="Team Archer",
                change_summary="Safe test upload",
                relative_paths='["' + '","'.join(item.filename for item in files) + '"]',
                files=files,
                user=self.user,
                db=db,
            )
        )

    def test_existing_version_is_rejected_before_any_storage_write(self):
        with patch("app.main.upload") as upload:
            with self.assertRaises(HTTPException) as raised:
                self.create([file("deck.txt")], Database(existing=object()))
        self.assertEqual(raised.exception.status_code, 409)
        upload.assert_not_called()

    def test_blank_metadata_is_rejected_before_any_storage_write(self):
        with patch("app.main.upload") as upload:
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(
                    main.create_presentation(
                        title="   ", version="V1", presentation_date=date.today(),
                        authors="Team Archer", change_summary="Safe test upload", relative_paths='["deck.txt"]',
                        files=[file("deck.txt")], user=self.user, db=Database(),
                    )
                )
        self.assertEqual(raised.exception.status_code, 422)
        upload.assert_not_called()

    def test_partial_upload_is_cleaned_when_a_later_file_is_invalid(self):
        with patch("app.main.upload"), patch("app.main.cleanup_new_objects") as cleanup:
            with self.assertRaises(HTTPException) as raised:
                self.create([file("valid.txt"), file("invalid.exe")], Database())
        self.assertEqual(raised.exception.status_code, 415)
        cleanup.assert_called_once()
        self.assertEqual(len(cleanup.call_args.args[0]), 1)

    def test_server_uses_extension_derived_content_type(self):
        db = Database()
        with patch("app.main.upload") as upload, patch("app.main.presentation_out", return_value={"id": 1}):
            result = self.create([file("notes.txt", content_type="text/html")], db)
        self.assertEqual(result, {"id": 1})
        self.assertEqual(upload.call_args.args[2], "text/plain; charset=utf-8")
