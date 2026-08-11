import re, uuid
import boto3
from botocore.exceptions import ClientError
from .config import get_settings

def client():
    s = get_settings()
    return boto3.client("s3", region_name=s.aws_region, endpoint_url=s.s3_endpoint_url, aws_access_key_id=s.aws_access_key_id, aws_secret_access_key=s.aws_secret_access_key)
def ensure_bucket():
    s = get_settings(); c = client()
    try: c.head_bucket(Bucket=s.s3_bucket)
    except ClientError:
        args = {"Bucket": s.s3_bucket}
        if s.aws_region != "us-east-1": args["CreateBucketConfiguration"] = {"LocationConstraint": s.aws_region}
        c.create_bucket(**args)
def safe_key(title: str, version: str, filename: str) -> str:
    clean = lambda x: re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"presentations/{clean(title)}/{clean(version)}/{uuid.uuid4().hex}.{suffix}"
def upload(key: str, data: bytes, content_type: str):
    s = get_settings(); ensure_bucket(); client().put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type)
def download_url(key: str) -> str:
    s = get_settings(); return client().generate_presigned_url("get_object", Params={"Bucket":s.s3_bucket,"Key":key}, ExpiresIn=3600)
