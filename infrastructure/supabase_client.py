import os
from supabase import create_client, Client
from core.config import SUPABASE_URL, SUPABASE_KEY

class SupabaseClient:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    @staticmethod
    def get_countries():
        return SupabaseClient.client.table("country").select("*").execute()
