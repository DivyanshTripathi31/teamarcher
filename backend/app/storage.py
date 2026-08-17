import re, uuid
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from .config import get_settings

def local_fallback_enabled() -> bool:
    endpoint = (get_settings().s3_endpoint_url or "").lower()
    return endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost")

def storage_configured() -> bool:
    s = get_settings()
    # On EC2, boto3 obtains temporary credentials from the instance role via
    # its default credential provider chain.  A bucket is the only required
    # application setting; an operation will report a useful AWS error if the
    # role is absent or lacks the required permission.
    return bool(s.s3_bucket)

def local_path(key: str) -> Optional[Path]:
    root = Path(get_settings().local_storage_dir).resolve()
    candidate = (root / key).resolve()
    if candidate == root or root not in candidate.parents:
        return None
    return candidate

def local_file(key: str) -> Optional[Path]:
    path = local_path(key)
    return path if path and path.is_file() else None

def local_url(key: str) -> str:
    base_url = get_settings().local_storage_public_base_url.rstrip("/")
    return f"{base_url}/api/files/{quote(key, safe='/')}"

def client():
    s = get_settings()
    if not storage_configured():
        raise RuntimeError("Object storage is not configured")

    client_args = {"region_name": s.aws_region}
    if s.s3_endpoint_url:
        client_args["endpoint_url"] = s.s3_endpoint_url

    # Static credentials remain supported only for local MinIO development.
    # Omitting these arguments entirely is essential for EC2 IAM-role auth.
    if bool(s.aws_access_key_id) != bool(s.aws_secret_access_key):
        raise RuntimeError("Both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required together")
    if s.aws_access_key_id:
        client_args["aws_access_key_id"] = s.aws_access_key_id
        client_args["aws_secret_access_key"] = s.aws_secret_access_key

    return boto3.client("s3", **client_args)


def ensure_bucket():
    s = get_settings()
    c = client()
    try:
        c.head_bucket(Bucket=s.s3_bucket)
    except ClientError:
        # The production bucket is pre-provisioned and private. The application
        # role deliberately has no CreateBucket permission. Preserve automatic
        # bucket creation solely for the local MinIO development endpoint.
        if not local_fallback_enabled():
            raise
        args = {"Bucket": s.s3_bucket}
        if s.aws_region != "us-east-1": args["CreateBucketConfiguration"] = {"LocationConstraint": s.aws_region}
        c.create_bucket(**args)
def safe_key(title: str, version: str, filename: str) -> str:
    clean = lambda x: re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"presentations/{clean(title)}/{clean(version)}/{uuid.uuid4().hex}.{suffix}"
def upload(key: str, data: bytes, content_type: str):
    s = get_settings()
    if not storage_configured() and not local_fallback_enabled():
        raise RuntimeError("Object storage is not configured")
    try:
        ensure_bucket()
        client().put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type)
    except (BotoCoreError, ClientError, OSError):
        if not local_fallback_enabled():
            raise
        path = local_path(key)
        if not path:
            raise ValueError("Invalid local storage key")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
def download_url(key: str, filename: Optional[str] = None) -> str:
    if local_file(key):
        return local_url(key)
    if not storage_configured():
        raise RuntimeError("Object storage is not configured")
    s = get_settings()
    params = {"Bucket":s.s3_bucket,"Key":key}
    if filename: params["ResponseContentDisposition"] = f'attachment; filename="{filename.replace(chr(34), "")}"'
    return client().generate_presigned_url("get_object", Params=params, ExpiresIn=3600)
def delete_many(keys: list[str]):
    unique_keys = list(dict.fromkeys(key for key in keys if key))
    if not unique_keys: return
    for key in unique_keys:
        path = local_file(key)
        if path:
            path.unlink()
    if not storage_configured():
        return
    s = get_settings()
    try:
        response = client().delete_objects(Bucket=s.s3_bucket, Delete={"Objects":[{"Key":key} for key in unique_keys], "Quiet":True})
        if response.get("Errors"):
            raise RuntimeError("S3 could not delete one or more stored objects")
    except (BotoCoreError, ClientError, OSError):
        if not local_fallback_enabled():
            raise
