import os
from supabase import create_client, Client

from core.config import SUPABASE_KEY, SUPABASE_URL


class SupabaseClient:
    client: Client = create_client(supabase_url=SUPABASE_URL,supabase_key= SUPABASE_KEY)

    @staticmethod
    def get_countries():
        return SupabaseClient.client.table("country").select("*").execute()

    @staticmethod
    def insert_notification(notification_data):
        return SupabaseClient.client.table("notifications").insert(notification_data).execute()

    @staticmethod
    def get_role_by_name(role_name: str):
        return SupabaseClient.client.table("role").select("*").eq("name", role_name).single().execute()