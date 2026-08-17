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
    def test_ec2_client_uses_default_credential_chain_with_regional_sigv4(self, boto_client, _get_settings):
        storage.client()
        boto_client.assert_called_once()
        args, kwargs = boto_client.call_args
        self.assertEqual(args, ("s3",))
        self.assertEqual(kwargs["region_name"], "ap-south-1")
        self.assertEqual(kwargs["endpoint_url"], "https://s3.ap-south-1.amazonaws.com")
        self.assertEqual(kwargs["config"].signature_version, "s3v4")
        self.assertEqual(kwargs["config"].s3["addressing_style"], "virtual")
        self.assertNotIn("aws_access_key_id", kwargs)
        self.assertNotIn("aws_secret_access_key", kwargs)

    @patch("app.storage.get_settings", return_value=settings(s3_endpoint_url="http://localhost:9000"))
    @patch("app.storage.boto3.client")
    def test_local_s3_endpoint_is_preserved(self, boto_client, _get_settings):
        storage.client()
        _args, kwargs = boto_client.call_args
        self.assertEqual(kwargs["endpoint_url"], "http://localhost:9000")
        self.assertNotIn("config", kwargs)

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
