from typing import Dict, Any
from supabase_client import is_supabase_configured
from r2_client import is_r2_configured
from qdrant_manager import get_qdrant_status


def get_health_status() -> Dict[str, Any]:
    """
    Checks the connectivity and status of external services (Supabase, R2, Qdrant).
    """
    return {
        "status": "online",
        "supabase_connected": is_supabase_configured(),
        "cloudflare_r2_connected": is_r2_configured(),
        "qdrant": get_qdrant_status(),
    }
