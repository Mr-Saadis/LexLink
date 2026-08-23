# backend/r2_client.py
"""
Cloudflare R2 Object Storage Client for LexLink.
Provides S3-compatible file storage for original judgment PDFs and artifacts.
"""

import os
from typing import Optional, Dict, Any, Union, BinaryIO
from dotenv import load_dotenv

# Load .env
def get_r2_config():
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "").strip()
    endpoint_url = os.getenv("CLOUDFLARE_R2_ENDPOINT_URL", "").strip()
    bucket_name = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "lexlink-backend").strip()
    public_domain = os.getenv("CLOUDFLARE_R2_PUBLIC_DOMAIN", "").strip()

    if not endpoint_url and account_id:
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

    return {
        "account_id": account_id,
        "access_key": access_key,
        "secret_key": secret_key,
        "endpoint_url": endpoint_url,
        "bucket_name": bucket_name,
        "public_domain": public_domain,
    }


def is_r2_configured() -> bool:
    """Checks if Cloudflare R2 credentials are fully configured."""
    cfg = get_r2_config()
    return bool(
        cfg["access_key"]
        and cfg["secret_key"]
        and (cfg["endpoint_url"] or cfg["account_id"])
    )


def get_r2_client():
    """
    Initializes and returns a boto3 client configured for Cloudflare R2 (S3-compatible API).
    """
    cfg = get_r2_config()
    if not is_r2_configured():
        return None

    try:
        import boto3
        from botocore.config import Config

        return boto3.client(
            service_name="s3",
            endpoint_url=cfg["endpoint_url"],
            aws_access_key_id=cfg["access_key"],
            aws_secret_access_key=cfg["secret_key"],
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    except ImportError:
        print("[Cloudflare R2] boto3 package not installed. Run `pip install boto3`.")
        return None
    except Exception as e:
        print(f"[Cloudflare R2] Failed to initialize R2 client: {e}")
        return None
    except ImportError:
        print("[Cloudflare R2] boto3 package not installed. Run `pip install boto3`.")
        return None
    except Exception as e:
        print(f"[Cloudflare R2] Failed to initialize R2 client: {e}")
        return None


def list_r2_buckets():
    """Lists all available buckets in the Cloudflare R2 account."""
    client = get_r2_client()
    if not client:
        return []
    try:
        response = client.list_buckets()
        return [b["Name"] for b in response.get("Buckets", [])]
    except Exception as e:
        print(f"[Cloudflare R2] Error listing buckets: {e}")
        return []


def ensure_bucket_exists(bucket_name: Optional[str] = None) -> bool:
    """
    Ensures the target bucket exists in R2. If it does not exist, attempts to create it.
    """
    client = get_r2_client()
    if not client:
        return False

    cfg = get_r2_config()
    target_bucket = bucket_name or cfg["bucket_name"]
    try:
        existing_buckets = list_r2_buckets()
        if target_bucket in existing_buckets:
            return True

        # Attempt to create
        client.create_bucket(Bucket=target_bucket)
        print(f"[Cloudflare R2] Created bucket '{target_bucket}' successfully.")
        return True
    except Exception as e:
        print(f"[Cloudflare R2] Could not verify/create bucket '{target_bucket}': {e}")
        return False


def upload_file_to_r2(
    file_data: Union[bytes, BinaryIO, str],
    object_name: str,
    content_type: str = "application/pdf",
    bucket_name: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Uploads a file (bytes, file-like object, or file path) to Cloudflare R2.
    Returns the public URL (if domain configured) or object key URI.
    """
    client = get_r2_client()
    if not client:
        print("[Cloudflare R2] Client unavailable. File not uploaded to R2.")
        return None

    cfg = get_r2_config()
    target_bucket = bucket_name or cfg["bucket_name"]
    extra_args = {"ContentType": content_type}
    if metadata:
        extra_args["Metadata"] = metadata

    try:
        if isinstance(file_data, str):
            # File path
            with open(file_data, "rb") as f:
                client.upload_fileobj(f, target_bucket, object_name, ExtraArgs=extra_args)
        elif isinstance(file_data, bytes):
            import io
            client.upload_fileobj(io.BytesIO(file_data), target_bucket, object_name, ExtraArgs=extra_args)
        else:
            # File-like object
            client.upload_fileobj(file_data, target_bucket, object_name, ExtraArgs=extra_args)

        print(f"[Cloudflare R2] Successfully uploaded '{object_name}' to bucket '{target_bucket}'.")

        # Return public URL if custom domain is set, otherwise return presigned URL or R2 reference
        if cfg["public_domain"]:
            domain = cfg["public_domain"].rstrip("/")
            return f"{domain}/{object_name}"
        
        # Return presigned URL (valid for 7 days = 604800s)
        try:
            presigned_url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": target_bucket, "Key": object_name},
                ExpiresIn=604800,  # 7 days max for S3 presigned url
            )
            return presigned_url
        except Exception:
            return f"r2://{target_bucket}/{object_name}"

    except Exception as e:
        print(f"[Cloudflare R2] Upload failed for '{object_name}': {e}")
        return None


def get_presigned_download_url(
    object_name: str,
    bucket_name: Optional[str] = None,
    expires_in: int = 3600,
) -> Optional[str]:
    """Generates a temporary signed URL for securely downloading/viewing a file from R2."""
    client = get_r2_client()
    if not client:
        return None

    cfg = get_r2_config()
    target_bucket = bucket_name or cfg["bucket_name"]
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": target_bucket, "Key": object_name},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as e:
        print(f"[Cloudflare R2] Failed to generate presigned URL: {e}")
        return None

