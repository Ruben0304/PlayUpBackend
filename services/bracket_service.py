from infrastructure.supabase_client import SupabaseClient
from typing import List, Dict, Any, Optional, Tuple
from domain.models import Match, BracketStage, BracketSlot, UnpairedTeam

class BracketService:
    def __init__(self):
        self.supabase = SupabaseClient()

    def cleanBracketsIfExist(self, tournament_season_id: int) -> int:
        response = self.supabase.client.rpc('delete_tournament_brackets', {
            'p_tournament_season_id': tournament_season_id
        }).execute()
            
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error removing brackets: {response.error.message}")
            
        return True

    def get_team_count(self, tournament_season_id: int) -> int:
        response = self.supabase.client.table('team_tournament') \
            .select('*', count='exact') \
            .eq('tournament_season', tournament_season_id) \
            .eq('in_competition', True) \
            .execute()
            
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error getting team count: {response.error.message}")
            
        return response.count or 0

    def get_fixture_rounds(self, num_rounds: int) -> List[Dict]:
        response = self.supabase.client.table('fixture_round') \
            .select('*') \
            .order('index', desc=False) \
            .limit(num_rounds) \
            .execute()
            
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error getting fixture rounds: {response.error.message}")
            
        fixture_rounds = response.data
        # Invertir el orden para que los primeros rounds (octavos) tengan el fixture_round con índice más alto
        # y los últimos rounds (final) tengan el fixture_round con índice más bajo
        fixture_rounds.reverse()
        
        print(f"Fixture rounds (invertidos): {fixture_rounds}")
        return fixture_rounds

    def get_teams_for_tournament(self, tournament_season_id: int) -> List[int]:
        response = self.supabase.client.table('team_tournament') \
            .select('team') \
            .eq('tournament_season', tournament_season_id) \
            .execute()
            
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error getting teams: {response.error.message}")
            
        return [t['team'] for t in response.data]

    def create_match_for_stage(self, tournament_season_id: int, stage: Dict, 
                             home_id: Optional[int] = None, away_id: Optional[int] = None) -> Dict:
        params = {
            'home_id': home_id,
            'away_id': away_id,
            'tournament_season_id': tournament_season_id,
            'match_status_id': 1,
            'referee': None,
            'date_match': None,
            'time_match': None,
            'location': None,
            'fixture_round_id': stage['fixture_round']
        }
        
        response = self.supabase.client.rpc('create_match', params).execute()
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error creating match: {response.error.message}")
            
        match_response = self.supabase.client.table('match') \
            .select('*') \
            .eq('tournament_season', tournament_season_id) \
            .eq('fixture_round', stage['fixture_round']) \
            .order('id', desc=True) \
            .limit(1) \
            .execute()
            
        if hasattr(match_response, 'error') and match_response.error or not match_response.data:
            raise Exception("Error getting created match")
            
        return match_response.data[0]

    def update_slot_match(self, slot_id: int, match_id: int):
        response = self.supabase.client.table('bracket_slot') \
            .update({'match': match_id}) \
            .eq('id', slot_id) \
            .execute()
            
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Error updating slot with match: {response.error.message}")

    def create_matches_for_stage(self, tournament_season_id: int, stage: Dict, 
                               slots: List[Dict], team_ids: List[int] = None, 
                               unpaired_teams: List[UnpairedTeam] = None) -> Tuple[List[Dict], List[UnpairedTeam]]:
        is_first_stage = bool(team_ids)
        new_unpaired_teams = []
        matches = []
        
        print(f"Creating matches for stage {stage['id']} with {len(slots)} slots")
        if is_first_stage:
            print(f"This is the first stage with {len(team_ids)} teams")

        for i, slot in enumerate(slots):
            print(f"Processing slot {i+1}/{len(slots)} (ID: {slot['id']})")
            
            # Check for unpaired team (only in first stage with odd number of teams)
            if is_first_stage and i >= len(team_ids) // 2:
                unpaired_team = team_ids[-1]
                print(f"Found unpaired team {unpaired_team}")
                
                # Create a match for the unpaired team where it's both the home team and winner
                print(f"Creating match for unpaired team {unpaired_team}")
                match = self.create_match_for_stage(tournament_season_id, stage, home_id=unpaired_team, away_id=None)
                print(f"Created match with ID {match['id']} for unpaired team")
                
                # Update the match_teams to set the unpaired team as the winner
                match_teams_id = match['match_teams']
                self.supabase.client.table('match_teams') \
                    .update({'winner': unpaired_team}) \
                    .eq('id', match_teams_id) \
                    .execute()
                print(f"Updated match_teams {match_teams_id} to set winner as {unpaired_team}")
                
                # Update the slot with the match
                self.update_slot_match(slot['id'], match['id'])
                print(f"Updated slot {slot['id']} with match {match['id']}")
                
                matches.append(match)
                
                # Check if this slot has a next_slot to advance the team to
                slot_response = self.supabase.client.table('bracket_slot') \
                    .select('next_slot') \
                    .eq('id', slot['id']) \
                    .single() \
                    .execute()

                if hasattr(slot_response, 'error') and slot_response.error:
                    print(f"Error getting next_slot: {slot_response.error.message}")
                
                if slot_response.data and slot_response.data['next_slot']:
                    next_slot = slot_response.data['next_slot']
                    print(f"Adding unpaired team {unpaired_team} with next_slot {next_slot}")
                    new_unpaired_teams.append(UnpairedTeam(team_id=unpaired_team, next_slot_id=next_slot))
                else:
                    print("Warning: No next_slot found for unpaired team")
                continue

            # Set teams for the first stage, otherwise leave null to be filled in later
            home_team = team_ids[i * 2] if is_first_stage and i * 2 < len(team_ids) else None
            away_team = team_ids[i * 2 + 1] if is_first_stage and i * 2 + 1 < len(team_ids) else None
            
            print(f"Creating match for slot {slot['id']} with home={home_team}, away={away_team}")
            
            # Create match for this slot
            match = self.create_match_for_stage(tournament_season_id, stage, home_team, away_team)
            print(f"Created match with ID {match['id']}")
            
            self.update_slot_match(slot['id'], match['id'])
            print(f"Updated slot {slot['id']} with match {match['id']}")
            
            matches.append(match)

        print(f"Created {len(matches)} matches for stage {stage['id']}")
        return matches, new_unpaired_teams

    def process_unpaired_teams(self, unpaired_teams: List[UnpairedTeam]):
        for unpaired_team in unpaired_teams:
            # Get the match associated with the next slot
            next_slot_match = self.supabase.client.table('bracket_slot') \
                .select('match') \
                .eq('id', unpaired_team.next_slot_id) \
                .single() \
                .execute()

            if next_slot_match.data and next_slot_match.data['match']:
                # Get the match record to find its match_teams_id
                match = self.supabase.client.table('match') \
                    .select('match_teams') \
                    .eq('id', next_slot_match.data['match']) \
                    .single() \
                    .execute()

                if match.data and match.data['match_teams']:
                    # Update the match_teams record to set the home team
                    match_teams_id = match.data['match_teams']
                    print(f"Setting unpaired team {unpaired_team.team_id} as home team in match_teams {match_teams_id}")
                    
                    self.supabase.client.table('match_teams') \
                        .update({'home': unpaired_team.team_id}) \
                        .eq('id', match_teams_id) \
                        .execute()

    def create_third_place_match(self, tournament_season_id: int, stage: Dict) -> Dict:
        # Create a single slot for the third place match
        slot_data = {
            'bracket_stage': stage['id'],
            'match': None,
            'next_slot': None,
            'is_third_place': True
        }
        
        slot_response = self.supabase.client.table('bracket_slot') \
            .insert(slot_data) \
            .execute()
        
        if hasattr(slot_response, 'error') and slot_response.error:
            raise Exception(f'Error creating third place slot: {slot_response.error.message}')
        
        slot = slot_response.data[0]
        
        # Create match for the third place slot
        match = self.create_match_for_stage(tournament_season_id, stage)
        
        # Update the slot with the match ID
        self.update_slot_match(slot['id'], match['id'])
        
        return match 