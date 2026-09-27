from supabase_client import get_supabase_client


def list_documents(limit: int = 50, offset: int = 0):
    """
    Fetches paginated list of ingested judgments/documents from Supabase.
    """
    client = get_supabase_client()
    if not client:
        return {"documents": [], "message": "Supabase not configured"}

    try:
        res = (
            client.table("documents")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"documents": res.data or []}
    except Exception as e:
        return {"error": str(e), "documents": []}
