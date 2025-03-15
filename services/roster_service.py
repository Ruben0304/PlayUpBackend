from infrastructure.supabase_client import SupabaseClient
from query_supabase import QuerySupabase


class RosterService:
    @staticmethod
    def get_roster_by_id(roster_id: int):
        return SupabaseClient.client.table('roster') \
            .select(QuerySupabase.roster) \
            .eq('id', roster_id) \
            .single() \
            .execute()
       