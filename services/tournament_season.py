from infrastructure.supabase_client import SupabaseClient
from domain.models import Match, TournamentSeason, OtherMatch
from .bracket_creator import BracketCreator
import os

class TournamentSeasonService:
    @staticmethod
    def create_bracket(payload):
        try:
            # Adaptamos para aceptar el nuevo formato de payload
            tournament_season_id = payload.get('tournamentSeasonId') or payload.get('tournament_season_id')
            matches = payload.get('matches', [])
            
            if not tournament_season_id:
                return {'status': 400, 'message': 'tournamentSeasonId es requerido'}
            
            bracket_creator = BracketCreator()
            
            # Si tenemos matches predefinidos, los usamos
            if matches:
                # Convertimos el formato si es necesario
                formatted_matches = []
                for match in matches:
                    home_id = match.get('home')
                    away_id = match.get('away')
                    
                    formatted_matches.append({
                        'home_id': home_id,
                        'away_id': away_id
                    })
                
                # Llamamos al método con los matches predefinidos
                result = bracket_creator.create_bracket_with_matches(tournament_season_id, formatted_matches)
            else:
                # Comportamiento original
                result = bracket_creator.create_bracket_structure(tournament_season_id)
            
            # Actualizar el campo is_matchs_generated a true en tournament_season
            print(f"Actualizando tournament_season {tournament_season_id} con is_matchs_generated=true")
            supabase = SupabaseClient()
            update_response = supabase.client.table('tournament_season') \
                .update({'is_matchs_generated': True}) \
                .eq('id', tournament_season_id) \
                .execute()
            
            if hasattr(update_response, 'error') and update_response.error:
                print(f"Error actualizando tournament_season: {update_response.error}")
                raise Exception(f"Error updating tournament_season: {update_response.error.message}")
            else:
                print("Campo is_matchs_generated actualizado correctamente")
                
            return result
            
        except Exception as error:
            print(f"Error in create_bracket: {error}")
            return {'status': 500, 'message': str(error)}

    @staticmethod
    def assign_team_to_next_slot(supabase, team_id, next_slot_id):
        print(f"Asignando equipo {team_id} al next_slot {next_slot_id}")
        # Primero obtener el match asociado al next_slot
        next_match = supabase.client.table('match').select('''
            id,
            match_teams (
                id,
                home,
                away
            )
        ''').eq('id', supabase.client.table('bracket_slot').select('match').eq('id', next_slot_id).single().execute().data['match'])\
           .single().execute()

        if next_match.data:
            update_field = 'away' if next_match.data['match_teams']['home'] is not None else 'home'
            supabase.client.table('match_teams').update({
                update_field: team_id
            }).eq('id', next_match.data['match_teams']['id']).execute()
            print(f'Team {team_id} assigned to next match as {update_field}')

    @staticmethod
    def assign_team_to_third_place(supabase, team_id, tournament_season_id):
        print(f"Asignando equipo {team_id} al partido por tercer lugar")
        
        # Primero encontrar el bracket_slot del tercer lugar
        third_place_slot = supabase.client.table('bracket_slot').select('''
            id,
            match,
            bracket_stage (
                tournament_season
            )
        ''').eq('bracket_stage.tournament_season', tournament_season_id)\
           .eq('is_third_place', True)\
           .single().execute()

        if third_place_slot and third_place_slot.data:
            # Luego obtener el match y sus teams
            third_place_match = supabase.client.table('match').select('''
                id,
                match_teams (
                    id,
                    home,
                    away
                )
            ''').eq('id', third_place_slot.data['match'])\
               .single().execute()

            if third_place_match.data:
                update_field = 'away' if third_place_match.data['match_teams']['home'] is not None else 'home'
                supabase.client.table('match_teams').update({
                    update_field: team_id
                }).eq('id', third_place_match.data['match_teams']['id']).execute()
                print(f'Team {team_id} assigned to third place match as {update_field}')

    @staticmethod
    def update_team_competition_status(supabase, team_id, tournament_season_id, is_winner):
        if not is_winner:
            update_response = supabase.client.table('team_tournament').update({
                'in_competition': False
            }).eq('team', team_id)\
              .eq('tournament_season', tournament_season_id)\
              .execute()
            print(f'Team {team_id} marked as eliminated from competition')

    @staticmethod
    def get_finished_statuses(supabase):
        finished_statuses = supabase.client.table('match_status').select('id').in_('short', ['FT', 'WO']).execute()
        if finished_statuses == None or not finished_statuses.data:
            raise ValueError('Match statuses not found')
        return finished_statuses.data

    @staticmethod
    def get_match_data(supabase, status_id):
        match_response = supabase.client.table('match').select('''
            id,
            goals:goals (
                home,
                away
            ),
            match_teams:match_teams (
                id,
                home,
                away
            ),
            tournament_season,
            fixture_round:fixture_round (
                id,
                round,
                stage:stage (
                    id,
                    name
                )
            )
        ''').eq('status', status_id).single().execute()
        
        if match_response == None:
            raise ValueError('Match not found')

        # Buscar bracket_slot a través de la relación correcta
        bracket_response = supabase.client.table('bracket_slot').select('''
            id,
            next_slot
        ''').eq('match', match_response.data['id']).single().execute()

        if bracket_response and bracket_response.data:
            match_response.data['bracket_slot'] = bracket_response.data

        return Match(**match_response.data)

    @staticmethod
    def get_tournament_double_round(supabase, tournament_season_id):
        response = supabase.client.table('tournament_season').select('''
            tournament_double_round (
                elimination,
                group_stage,
                round_robin
            )
        ''').eq('id', tournament_season_id).single().execute()
        
        if response == None:
            raise ValueError('Tournament season not found')
        return TournamentSeason(**response.data)

    @staticmethod
    def get_other_match(supabase, match, finished_status_ids):
        response = supabase.client.table('match').select('''
            id,
            goals (home, away),
            match_teams!inner (home, away)
        ''').eq('tournament_season', match.tournament_season)\
           .eq('fixture_round', match.fixture_round.id)\
           .neq('id', match.id)\
           .eq('match_teams.home', match.match_teams.away)\
           .eq('match_teams.away', match.match_teams.home)\
           .in_('status', [s['id'] for s in finished_status_ids])\
           .execute()
        
        if response == None:
            raise ValueError('Error getting other matches')
        return [OtherMatch(**m) for m in response.data]

    @staticmethod
    def update_match_winner(supabase, match_teams_id, winner_id):
        response = supabase.client.table('match_teams').update({
            'winner': winner_id
        }).eq('id', match_teams_id).execute()
        
        if response == None:
            raise ValueError('Error updating winner')
        return response.data

    @staticmethod
    def handle_double_round_match(supabase, match, other_match):
        total_home = match.goals.home + other_match.goals.away
        total_away = match.goals.away + other_match.goals.home
        
        if total_home > total_away:
            TournamentSeasonService.update_match_winner(supabase, match.match_teams.id, match.match_teams.home)
            return match.match_teams.home, match.match_teams.away
        elif total_away > total_home:
            TournamentSeasonService.update_match_winner(supabase, match.match_teams.id, match.match_teams.away)
            return match.match_teams.away, match.match_teams.home
        return None, None

    @staticmethod
    def handle_single_match(supabase, match):
        if match.goals.home > match.goals.away:
            TournamentSeasonService.update_match_winner(supabase, match.match_teams.id, match.match_teams.home)
            return match.match_teams.home, match.match_teams.away
        elif match.goals.away > match.goals.home:
            TournamentSeasonService.update_match_winner(supabase, match.match_teams.id, match.match_teams.away)
            return match.match_teams.away, match.match_teams.home
        return None, None

    @staticmethod
    def handle_match_finished(payload):
        try:
            supabase = SupabaseClient()
            status_id = payload['record']['id']
            
            finished_statuses = TournamentSeasonService.get_finished_statuses(supabase)
            match = TournamentSeasonService.get_match_data(supabase, status_id)
            tournament_season = TournamentSeasonService.get_tournament_double_round(supabase, match.tournament_season)
            
            is_double_round = getattr(tournament_season.tournament_double_round, match.fixture_round.stage.name, False)
            winner_id, loser_id = None, None

            if is_double_round:
                other_matches = TournamentSeasonService.get_other_match(supabase, match, finished_statuses)
                if other_matches:
                    winner_id, loser_id = TournamentSeasonService.handle_double_round_match(supabase, match, other_matches[0])
            else:
                winner_id, loser_id = TournamentSeasonService.handle_single_match(supabase, match)

            if winner_id and loser_id:
                TournamentSeasonService.update_team_competition_status(supabase, loser_id, match.tournament_season, False)
                if match.fixture_round.round == 'semifinal':
                    TournamentSeasonService.assign_team_to_next_slot(supabase, winner_id, match.bracket_slot.next_slot)
                    TournamentSeasonService.assign_team_to_third_place(supabase, loser_id, match.tournament_season)

            return {'status': 200, 'message': 'Success'}
        except Exception as error:
            print('Function error:', error)         
            return {'status': 500, 'message': str(error)}
