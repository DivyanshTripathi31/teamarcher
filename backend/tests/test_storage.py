import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from app import storage


def settings(**overrides):
    values = {
        "s3_bucket": "teamarcher-test-bucket",
        "aws_region": "ap-south-1",
        "s3_endpoint_url": None,
        "aws_access_key_id": "",
        "aws_secret_access_key": "",
        "local_storage_dir": "/tmp/teamarcher-storage-tests",
        "local_storage_public_base_url": "http://127.0.0.1:8000",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class StorageTests(unittest.TestCase):
    @patch("app.storage.get_settings", return_value=settings())
    @patch("app.storage.boto3.client")
    def test_ec2_client_uses_default_credential_chain(self, boto_client, _get_settings):
        storage.client()
        boto_client.assert_called_once_with("s3", region_name="ap-south-1")

    @patch("app.storage.get_settings", return_value=settings())
    def test_production_bucket_is_not_created_by_application(self, _get_settings):
        s3 = Mock()
        s3.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadBucket")
        with patch("app.storage.client", return_value=s3):
            with self.assertRaises(ClientError):
                storage.ensure_bucket()
        s3.create_bucket.assert_not_called()

    @patch("app.storage.local_file", return_value=None)
    @patch("app.storage.get_settings", return_value=settings())
    def test_partial_s3_delete_is_reported(self, _get_settings, _local_file):
        s3 = Mock()
        s3.delete_objects.return_value = {"Errors": [{"Key": "a", "Code": "AccessDenied"}]}
        with patch("app.storage.client", return_value=s3):
            with self.assertRaisesRegex(RuntimeError, "could not delete"):
                storage.delete_many(["a"])


if __name__ == "__main__":
    unittest.main()
