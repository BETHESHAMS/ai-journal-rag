import logging
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger("ai_journal.database")

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Returns a singleton instance of the Supabase Client.
    Uses the service role key to manage relational records and vector searches.
    """
    global _supabase_client
    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            logger.warning(
                "SUPABASE_URL or SUPABASE_SERVICE_KEY is missing in .env! "
                "Database and Vector operations will fail until valid credentials are provided."
            )
        _supabase_client = create_client(
            supabase_url=settings.SUPABASE_URL or "https://placeholder.supabase.co",
            supabase_key=settings.SUPABASE_SERVICE_KEY or "placeholder-key"
        )
    return _supabase_client
