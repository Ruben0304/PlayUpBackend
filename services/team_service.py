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
            
    @staticmethod
    def add_player_to_roster(payload):
       
        player_id = payload['player_id']
        team_id = payload['team_id']
        tournament_season_id = payload['tournament_season_id']
        
        # Obtener el id del torneo del equipo
        team_tournament_result = (SupabaseClient.client
            .table("team_tournament")
            .select("id")
            .eq("team", team_id)
            .eq("tournament_season", tournament_season_id)
            .single()
            .execute())
        
        if not team_tournament_result.data or len(team_tournament_result.data) == 0:
            raise Exception("team_tournament not found")
        
        team_tournament_id = team_tournament_result.data["id"]
        print(f"team_tournament_id: {team_tournament_id}")  # Depuración
        
        # Verificar si el jugador ya existe en el torneo
        player_exists_result = (SupabaseClient.client
            .table("roster")
            .select("id, team_tournament(tournament_season)")
            .eq("player", player_id)
            .eq("team_tournament.tournament_season", tournament_season_id)
            .execute())
        
        player_exists = len(player_exists_result.data) > 0
        print(f"player_exists: {player_exists}")  # Depuración
        
        # Si el jugador ya existe, devolver un error
        if player_exists:
            raise Exception(f"player_already_registered_in_tournament: {player_id}")
        
        # Preparar los datos para insertar
        roster_data = {
            "player": player_id,
            "team_tournament": team_tournament_id
        }
        
        # Si player_position_id no está en el payload o es None, obtener la posición del jugador
        if 'player_position_id' not in payload or payload['player_position_id'] is None:
            # Obtener la posición del jugador desde la tabla player
            player_result = (SupabaseClient.client
                .table("player")
                .select("position")
                .eq("id", player_id)
                .single()
                .execute())
            
            if player_result.data and "position" in player_result.data and player_result.data["position"] is not None:
                roster_data["player_position"] = player_result.data["position"]
        else:
            # Usar la posición proporcionada en el payload
            roster_data["player_position"] = payload['player_position_id']
        
        # Agregar número si está presente
        if 'number_value' in payload and payload['number_value'] is not None:
            roster_data["number"] = payload['number_value']
        
        # Insertar el jugador en el roster
        roster_result = (SupabaseClient.client
            .table("roster")
            .insert(roster_data)
            .execute())
        
        # Insertar el jugador en player_stats
        stats_result = (SupabaseClient.client
            .table("player_stats")
            .insert({
                "player": player_id,
                "team_tournament": team_tournament_id
            })
            .execute())
        
        return {"roster": roster_result.data, "stats": stats_result.data}
