from error.error_handling import ErrorTypes
from infrastructure.supabase_client import SupabaseClient
from services.tournament_season import TournamentSeasonService
from services.roster_service import RosterService


class TeamService:
    @staticmethod
    def remove_player_from_roster(roster_id: int):
        roster = RosterService.get_roster_by_id(roster_id)
        is_active = TournamentSeasonService.is_active(roster.data['team_tournament']['tournament_season']['id'])
        
        if roster.data['is_active'] is False:
            raise Exception(ErrorTypes.player_already_eliminated_of_roster)
        
        if is_active is False:
            raise Exception(ErrorTypes.tournament_not_active)
        
        SupabaseClient.client.table('roster') \
            .update({'is_active': False}) \
            .eq('id', roster_id) \
            .execute()
