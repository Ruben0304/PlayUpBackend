from math import ceil, log2
from typing import Dict, List, Any
from .bracket_service import BracketService

class BracketCreator:
    def __init__(self):
        self.bracket_service = BracketService()

    def create_bracket_structure(self, tournament_season_id: int) -> Dict[str, Any]:
        try:
            # Get tournament info
            tournament_season = self.bracket_service.supabase.client.table('tournament_season') \
                .select('tournament_structure(has_third_place)') \
                .eq('id', tournament_season_id) \
                .single() \
                .execute()

            if hasattr(tournament_season, 'error') and tournament_season.error:
                raise Exception('Error getting tournament information')

            has_third_place = tournament_season.data['tournament_structure']['has_third_place']

            # Get teams and count
            team_ids = self.bracket_service.get_teams_for_tournament(tournament_season_id)
            num_teams = self.bracket_service.get_team_count(tournament_season_id)

            if num_teams < 2:
                raise Exception(f'Not enough teams to create brackets (found {num_teams})')

            # Calculate rounds and get fixture rounds
            total_rounds = ceil(log2(num_teams))
            fixture_rounds = self.bracket_service.get_fixture_rounds(total_rounds)

            # Create stages
            stages_data = [
                {'tournament_season': tournament_season_id, 'fixture_round': fr['id']}
                for fr in fixture_rounds
            ]

            # First insert the stages
            insert_response = self.bracket_service.supabase.client.table('bracket_stage') \
                .insert(stages_data) \
                .execute()

            if hasattr(insert_response, 'error') and insert_response.error:
                raise Exception(f'Error creating bracket stages: {insert_response.error.message}')

            # Then fetch the inserted stages
            stages_response = self.bracket_service.supabase.client.table('bracket_stage') \
                .select('*') \
                .eq('tournament_season', tournament_season_id) \
                .order('id') \
                .execute()

            if hasattr(stages_response, 'error') and stages_response.error:
                raise Exception(f'Error fetching bracket stages: {stages_response.error.message}')

            stages = stages_response.data

            # Create slots for each stage
            slots = []
            for i in range(total_rounds):
                num_matches = int(2 ** (total_rounds - i - 1))
                for j in range(num_matches):
                    slots.append({
                        'bracket_stage': stages[i]['id'],
                        'match': None,
                        'next_slot': None
                    })

            # First insert the slots
            insert_slots_response = self.bracket_service.supabase.client.table('bracket_slot') \
                .insert(slots) \
                .execute()

            if hasattr(insert_slots_response, 'error') and insert_slots_response.error:
                raise Exception('Error creating bracket slots')

            # Then fetch the inserted slots
            slots_response = self.bracket_service.supabase.client.table('bracket_slot') \
                .select('*, bracket_stage!inner(*)') \
                .eq('bracket_stage.tournament_season', tournament_season_id) \
                .execute()

            if hasattr(slots_response, 'error') and slots_response.error:
                raise Exception(f'Error fetching bracket slots: {slots_response.error.message}')
                
            print(f"Retrieved {len(slots_response.data)} slots after insertion")
            created_slots = slots_response.data

            # Update next_slot references
            for i in range(len(stages) - 1):
                print(f"Filtering slots for stage {stages[i]['id']}")
                # Printing some details to debug
                if len(created_slots) > 0:
                    print(f"First slot structure: {created_slots[0].keys()}")
                    print(f"Bracket stage structure: {created_slots[0]['bracket_stage'].keys()}")
                
                current_stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == stages[i]['id']]
                next_stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == stages[i + 1]['id']]
                
                print(f"Stage {i+1}: Linking {len(current_stage_slots)} slots to {len(next_stage_slots)} next stage slots")

                # Link current stage slots to next stage slots
                for j in range(0, len(current_stage_slots), 2):
                    if j//2 < len(next_stage_slots):
                        next_slot_id = next_stage_slots[j//2]['id']
                        
                        # Update the first slot
                        if j < len(current_stage_slots):
                            current_slot_id = current_stage_slots[j]['id']
                            # Verificar que el next_slot no sea el mismo que el slot actual
                            if current_slot_id != next_slot_id:
                                print(f"Updating slot {current_slot_id} with next_slot {next_slot_id}")
                                slot_response = self.bracket_service.supabase.client.table('bracket_slot') \
                                    .update({'next_slot': next_slot_id}) \
                                    .eq('id', current_slot_id) \
                                    .execute()
                                    
                                if hasattr(slot_response, 'error') and slot_response.error:
                                    print(f"Error updating first slot: {slot_response.error.message}")
                            else:
                                print(f"WARNING: Skipping update because slot {current_slot_id} cannot reference itself as next_slot")
                        
                        # Update the second slot
                        if j + 1 < len(current_stage_slots):
                            current_slot_id = current_stage_slots[j+1]['id']
                            # Verificar que el next_slot no sea el mismo que el slot actual
                            if current_slot_id != next_slot_id:
                                print(f"Updating slot {current_slot_id} with next_slot {next_slot_id}")
                                slot_response = self.bracket_service.supabase.client.table('bracket_slot') \
                                    .update({'next_slot': next_slot_id}) \
                                    .eq('id', current_slot_id) \
                                    .execute()
                                    
                                if hasattr(slot_response, 'error') and slot_response.error:
                                    print(f"Error updating second slot: {slot_response.error.message}")
                            else:
                                print(f"WARNING: Skipping update because slot {current_slot_id} cannot reference itself as next_slot")

            # Create matches and handle unpaired teams
            unpaired_teams = []
            for stage in stages:
                print(f"Filtering slots for stage {stage['id']} to create matches")
                stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == stage['id']]
                print(f"Found {len(stage_slots)} slots for stage {stage['id']}")
                
                matches, new_unpaired_teams = self.bracket_service.create_matches_for_stage(
                    tournament_season_id,
                    stage,
                    stage_slots,
                    team_ids if stage == stages[0] else None,
                    unpaired_teams
                )
                unpaired_teams.extend(new_unpaired_teams)

            # Process unpaired teams
            self.bracket_service.process_unpaired_teams(unpaired_teams)

            # Create third place match if needed
            if has_third_place:
                final_stage = stages[-1]
                self.bracket_service.create_third_place_match(tournament_season_id, final_stage)

            return {
                'stages': stages,
                'slots': len(created_slots) + (1 if has_third_place else 0),
                'has_third_place': has_third_place
            }

        except Exception as error:
            print(f"Error in create_bracket_structure: {error}")
            raise 