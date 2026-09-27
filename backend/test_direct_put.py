import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

endpoint = os.getenv("CLOUDFLARE_R2_ENDPOINT_URL")
access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
secret_key = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
bucket_name = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "lexlink-judgments")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="auto",
    config=Config(signature_version="s3v4"),
)

print(f"Testing bucket: '{bucket_name}' at {endpoint}")

try:
    s3.put_object(Bucket=bucket_name, Key="test.txt", Body=b"hello world")
    print("[SUCCESS] Direct PutObject worked!")
except ClientError as e:
    print(f"[ERROR] Code: {e.response['Error']['Code']}, Message: {e.response['Error']['Message']}")
