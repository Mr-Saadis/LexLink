# backend/test_cloudflare.py
"""
Diagnostic test script to verify Cloudflare API Token and R2 S3 Object Storage connection.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
R2_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
R2_ENDPOINT = os.getenv("CLOUDFLARE_R2_ENDPOINT_URL")
BUCKET_NAME = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "lexlink-judgments")


def test_cloudflare_api_token():
    print("\n--- 1. Testing Cloudflare API Token Verification ---")
    if not API_TOKEN:
        print("[FAIL] CLOUDFLARE_API_TOKEN is not set.")
        return False

    url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("success"):
            print("[SUCCESS] Cloudflare API Token is VALID and ACTIVE!")
            print(f"Token status: {data.get('result', {}).get('status')}")
            return True
        else:
            print(f"[FAIL] Token verification response: {data}")
            return False
    except Exception as e:
        print(f"[ERROR] API Token request error: {e}")
        return False


def test_r2_storage():
    print("\n--- 2. Testing Cloudflare R2 S3-Compatible Connection ---")
    try:
        from r2_client import get_r2_client, list_r2_buckets, ensure_bucket_exists, upload_file_to_r2
    except ImportError as e:
        print(f"[FAIL] Could not import r2_client: {e}")
        return False

    client = get_r2_client()
    if not client:
        print("[FAIL] Could not initialize R2 client.")
        return False

    print("[OK] R2 Boto3 client initialized successfully.")

    # List buckets
    buckets = list_r2_buckets()
    print(f"[INFO] Existing R2 Buckets: {buckets}")

    # Ensure bucket exists
    print(f"[INFO] Ensuring bucket '{BUCKET_NAME}' exists...")
    bucket_ok = ensure_bucket_exists(BUCKET_NAME)
    if bucket_ok:
        print(f"[SUCCESS] Bucket '{BUCKET_NAME}' is ready!")
    else:
        print(f"[WARN] Could not automatically create bucket '{BUCKET_NAME}'. It might need manual creation in the Cloudflare R2 dashboard.")

    # Upload small test ping file
    test_content = b"LexLink Cloudflare R2 Connection Test - OK\n"
    test_key = "test_ping.txt"
    print(f"[INFO] Uploading test file '{test_key}' to R2...")
    url = upload_file_to_r2(test_content, test_key, content_type="text/plain")
    if url:
        print(f"[SUCCESS] File uploaded successfully!")
        print(f"[INFO] Generated URL: {url[:100]}...")
        return True
    else:
        print("[FAIL] Test file upload failed.")
        return False


if __name__ == "__main__":
    print("========================================")
    print("   LexLink Cloudflare Verification")
    print("========================================")
    api_ok = test_cloudflare_api_token()
    r2_ok = test_r2_storage()
    print("\n========================================")
    print(f"Result -> API Token: {'PASSED' if api_ok else 'FAILED'} | R2 S3: {'PASSED' if r2_ok else 'FAILED'}")
    print("========================================")
