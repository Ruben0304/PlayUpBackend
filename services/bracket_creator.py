from math import ceil, log2
from typing import Dict, List, Any
from .bracket_service import BracketService
import random
from domain.models import UnpairedTeam

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

            # Aleatoriza la lista de team_ids
            random.shuffle(team_ids)

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

    def create_bracket_with_matches(self, tournament_season_id: int, predefined_matches: list) -> Dict[str, Any]:
        try:
            from math import ceil, log2
            
            print("Iniciando create_bracket_with_matches con matches predefinidos")
            
            # Get tournament info
            tournament_season = self.bracket_service.supabase.client.table('tournament_season') \
                .select('tournament_structure(has_third_place)') \
                .eq('id', tournament_season_id) \
                .single() \
                .execute()

            if hasattr(tournament_season, 'error') and tournament_season.error:
                print(f"Error getting tournament info: {tournament_season.error}")
                raise Exception('Error getting tournament information')

            has_third_place = tournament_season.data['tournament_structure']['has_third_place']
            print(f"Has third place: {has_third_place}")

            # Extraer team_ids de los matches predefinidos
            team_ids = []
            for match in predefined_matches:
                if match['home_id'] not in team_ids and match['home_id'] is not None:
                    team_ids.append(match['home_id'])
                if match['away_id'] not in team_ids and match['away_id'] is not None:
                    team_ids.append(match['away_id'])
            
            num_teams = len(team_ids)
            print(f"Equipos extraídos: {team_ids}, total: {num_teams}")
            
            if num_teams < 2:
                raise Exception(f'Not enough teams to create brackets (found {num_teams})')

            # Calculate rounds y get fixture rounds
            total_rounds = ceil(log2(num_teams))
            fixture_rounds = self.bracket_service.get_fixture_rounds(total_rounds)
            print(f"Total rounds: {total_rounds}")
            print(f"Fixture rounds: {fixture_rounds}")

            # Create stages
            stages_data = [
                {'tournament_season': tournament_season_id, 'fixture_round': fr['id']}
                for fr in fixture_rounds
            ]
            print(f"Stages data to insert: {stages_data}")

            # Insert the stages
            insert_response = self.bracket_service.supabase.client.table('bracket_stage') \
                .insert(stages_data) \
                .execute()

            if hasattr(insert_response, 'error') and insert_response.error:
                print(f"Error inserting stages: {insert_response.error}")
                raise Exception(f'Error creating bracket stages: {insert_response.error.message}')

            # Then fetch the inserted stages
            stages_response = self.bracket_service.supabase.client.table('bracket_stage') \
                .select('*') \
                .eq('tournament_season', tournament_season_id) \
                .order('id') \
                .execute()

            if hasattr(stages_response, 'error') and stages_response.error:
                print(f"Error fetching stages: {stages_response.error}")
                raise Exception(f'Error fetching bracket stages: {stages_response.error.message}')

            stages = stages_response.data
            print(f"Inserted stages: {stages}")

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
            print(f"Slots to insert: {len(slots)}")

            # Insert the slots
            insert_slots_response = self.bracket_service.supabase.client.table('bracket_slot') \
                .insert(slots) \
                .execute()

            if hasattr(insert_slots_response, 'error') and insert_slots_response.error:
                print(f"Error inserting slots: {insert_slots_response.error}")
                raise Exception('Error creating bracket slots')

            # Fetch the inserted slots
            slots_response = self.bracket_service.supabase.client.table('bracket_slot') \
                .select('*, bracket_stage!inner(*)') \
                .eq('bracket_stage.tournament_season', tournament_season_id) \
                .execute()

            if hasattr(slots_response, 'error') and slots_response.error:
                print(f"Error fetching slots: {slots_response.error}")
                raise Exception(f'Error fetching bracket slots: {slots_response.error.message}')
            
            created_slots = slots_response.data
            print(f"Inserted slots count: {len(created_slots)}")

            # Update next_slot references
            for i in range(len(stages) - 1):
                current_stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == stages[i]['id']]
                next_stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == stages[i + 1]['id']]
                print(f"Updating next_slot for stage {i+1}: {len(current_stage_slots)} slots to {len(next_stage_slots)} next slots")

                # Link current stage slots to next stage slots
                for j in range(0, len(current_stage_slots), 2):
                    if j//2 < len(next_stage_slots):
                        next_slot_id = next_stage_slots[j//2]['id']
                        
                        # Update the first slot
                        if j < len(current_stage_slots):
                            current_slot_id = current_stage_slots[j]['id']
                            if current_slot_id != next_slot_id:
                                print(f"Updating slot {current_slot_id} with next_slot {next_slot_id}")
                                try:
                                    self.bracket_service.supabase.client.table('bracket_slot') \
                                        .update({'next_slot': next_slot_id}) \
                                        .eq('id', current_slot_id) \
                                        .execute()
                                    # Actualizar también el objeto en memoria
                                    for slot in created_slots:
                                        if slot['id'] == current_slot_id:
                                            slot['next_slot'] = next_slot_id
                                except Exception as e:
                                    print(f"Error updating slot {current_slot_id} with next_slot {next_slot_id}: {e}")
                        
                        # Update the second slot
                        if j + 1 < len(current_stage_slots):
                            current_slot_id = current_stage_slots[j+1]['id']
                            if current_slot_id != next_slot_id:
                                print(f"Updating slot {current_slot_id} with next_slot {next_slot_id}")
                                try:
                                    self.bracket_service.supabase.client.table('bracket_slot') \
                                        .update({'next_slot': next_slot_id}) \
                                        .eq('id', current_slot_id) \
                                        .execute()
                                    # Actualizar también el objeto en memoria
                                    for slot in created_slots:
                                        if slot['id'] == current_slot_id:
                                            slot['next_slot'] = next_slot_id
                                except Exception as e:
                                    print(f"Error updating slot {current_slot_id} with next_slot {next_slot_id}: {e}")

            # Volver a obtener los slots actualizados para asegurarnos de tener los next_slot correctos
            print("Obteniendo slots actualizados con next_slot...")
            updated_slots_response = self.bracket_service.supabase.client.table('bracket_slot') \
                .select('*, bracket_stage!inner(*)') \
                .eq('bracket_stage.tournament_season', tournament_season_id) \
                .execute()
            
            if hasattr(updated_slots_response, 'error') and updated_slots_response.error:
                print(f"Error fetching updated slots: {updated_slots_response.error}")
                raise Exception(f'Error fetching updated bracket slots: {updated_slots_response.error.message}')
            
            created_slots = updated_slots_response.data
            print(f"Slots actualizados obtenidos: {len(created_slots)}")
            
            # Verificar que los next_slot estén correctamente asignados
            slots_with_next = [s for s in created_slots if s['next_slot'] is not None]
            print(f"Slots con next_slot asignado: {len(slots_with_next)} de {len(created_slots)}")

            # Preparar los equipos para la primera ronda
            first_stage = stages[0]
            first_stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == first_stage['id']]
            print(f"Slots para primera ronda: {len(first_stage_slots)}")
            
            # Lista para equipos sin pareja que necesitan avanzar
            unpaired_teams = []
            
            # Crear matches para la primera ronda
            for i, match_data in enumerate(predefined_matches):
                if i < len(first_stage_slots):
                    slot = first_stage_slots[i]
                    home_id = match_data['home_id']
                    away_id = match_data['away_id']
                    
                    print(f"Creando match para slot {slot['id']} con home={home_id}, away={away_id}")
                    
                    # Verificar si es un equipo bye (sin oponente)
                    is_bye = away_id is None
                    
                    # Usar RPC para crear match
                    params = {
                        'home_id': home_id,
                        'away_id': away_id,
                        'tournament_season_id': tournament_season_id,
                        'match_status_id': 1,
                        'referee': None,
                        'date_match': None,
                        'time_match': None,
                        'location': None,
                        'fixture_round_id': first_stage['fixture_round']
                    }
                    
                    response = self.bracket_service.supabase.client.rpc('create_match', params).execute()
                    if hasattr(response, 'error') and response.error:
                        print(f"Error creando match: {response.error}")
                        raise Exception(f"Error creating match: {response.error.message}")
                    
                    # Obtener el match recién creado
                    match_response = self.bracket_service.supabase.client.table('match') \
                        .select('*, match_teams(*)') \
                        .eq('tournament_season', tournament_season_id) \
                        .eq('fixture_round', first_stage['fixture_round']) \
                        .order('id', desc=True) \
                        .limit(1) \
                        .execute()
                    
                    if hasattr(match_response, 'error') and match_response.error or not match_response.data:
                        print("Error obteniendo match creado")
                        raise Exception("Error getting created match")
                    
                    match = match_response.data[0]
                    match_id = match['id']
                    match_teams_id = match['match_teams']['id']
                    
                    # Actualizar slot con match
                    self.bracket_service.supabase.client.table('bracket_slot') \
                        .update({'match': match_id}) \
                        .eq('id', slot['id']) \
                        .execute()
                    
                    # Si es un equipo bye, marcarlo como ganador y agregarlo a unpaired_teams
                    if is_bye:
                        print(f"Equipo bye detectado: {home_id}")
                        
                        # Marcar como ganador
                        self.bracket_service.supabase.client.table('match_teams') \
                            .update({'winner': home_id}) \
                            .eq('id', match_teams_id) \
                            .execute()
                        
                        # Obtener el next_slot para este slot
                        next_slot_id = slot.get('next_slot')
                        if next_slot_id:
                            print(f"Agregando equipo bye {home_id} a unpaired_teams con next_slot {next_slot_id}")
                            unpaired_teams.append(UnpairedTeam(team_id=home_id, next_slot_id=next_slot_id))
                        else:
                            print(f"ADVERTENCIA: No se encontró next_slot para el equipo bye {home_id} en memoria")
                            # Intentar obtener el next_slot directamente de la base de datos
                            slot_db = self.bracket_service.supabase.client.table('bracket_slot') \
                                .select('next_slot') \
                                .eq('id', slot['id']) \
                                .single() \
                                .execute()
                            
                            if slot_db.data and slot_db.data['next_slot']:
                                next_slot_id = slot_db.data['next_slot']
                                print(f"Encontrado next_slot {next_slot_id} en la base de datos para el equipo bye {home_id}")
                                unpaired_teams.append(UnpairedTeam(team_id=home_id, next_slot_id=next_slot_id))
                            else:
                                print(f"ERROR: No se pudo encontrar next_slot para el equipo bye {home_id} ni en memoria ni en la base de datos")

            # Crear matches vacíos para las rondas siguientes
            for i in range(1, len(stages)):
                stage = stages[i]
                stage_slots = [s for s in created_slots if s['bracket_stage']['id'] == stage['id']]
                print(f"Creating matches for stage {i+1}: {len(stage_slots)} slots")
                
                for slot in stage_slots:
                    print(f"Creating empty match for slot {slot['id']}")
                    
                    # Crear matches vacíos para esta etapa
                    params = {
                        'home_id': None,
                        'away_id': None,
                        'tournament_season_id': tournament_season_id,
                        'match_status_id': 1,
                        'referee': None,
                        'date_match': None,
                        'time_match': None,
                        'location': None,
                        'fixture_round_id': stage['fixture_round']
                    }
                    
                    response = self.bracket_service.supabase.client.rpc('create_match', params).execute()
                    
                    # Obtener el match recién creado
                    match_response = self.bracket_service.supabase.client.table('match') \
                        .select('*') \
                        .eq('tournament_season', tournament_season_id) \
                        .eq('fixture_round', stage['fixture_round']) \
                        .order('id', desc=True) \
                        .limit(1) \
                        .execute()
                    
                    match_id = match_response.data[0]['id']
                    
                    # Actualizar slot con match
                    self.bracket_service.supabase.client.table('bracket_slot') \
                        .update({'match': match_id}) \
                        .eq('id', slot['id']) \
                        .execute()

            # Procesar equipos sin pareja (avanzarlos a la siguiente ronda)
            if unpaired_teams:
                print(f"Procesando {len(unpaired_teams)} equipos sin pareja")
                for unpaired_team in unpaired_teams:
                    print(f"Avanzando equipo {unpaired_team.team_id} al next_slot {unpaired_team.next_slot_id}")
                    
                    # Obtener el match asociado al next_slot
                    next_slot_match = self.bracket_service.supabase.client.table('bracket_slot') \
                        .select('match') \
                        .eq('id', unpaired_team.next_slot_id) \
                        .single() \
                        .execute()
                    
                    if next_slot_match.data and next_slot_match.data['match']:
                        match_id = next_slot_match.data['match']
                        print(f"Match encontrado para next_slot: {match_id}")
                        
                        # Obtener el match_teams_id
                        match = self.bracket_service.supabase.client.table('match') \
                            .select('match_teams') \
                            .eq('id', match_id) \
                            .single() \
                            .execute()
                        
                        if match.data and match.data['match_teams']:
                            match_teams_id = match.data['match_teams']
                            
                            # Verificar si ya hay un equipo asignado como home
                            match_teams = self.bracket_service.supabase.client.table('match_teams') \
                                .select('home, away') \
                                .eq('id', match_teams_id) \
                                .single() \
                                .execute()
                            
                            if match_teams.data:
                                home_id = match_teams.data.get('home')
                                away_id = match_teams.data.get('away')
                                
                                # Decidir si asignar como home o away
                                if home_id is None:
                                    # Actualizar match_teams para asignar el equipo como home
                                    print(f"Asignando equipo {unpaired_team.team_id} como home en match_teams {match_teams_id}")
                                    self.bracket_service.supabase.client.table('match_teams') \
                                        .update({'home': unpaired_team.team_id}) \
                                        .eq('id', match_teams_id) \
                                        .execute()
                                elif away_id is None:
                                    # Actualizar match_teams para asignar el equipo como away
                                    print(f"Asignando equipo {unpaired_team.team_id} como away en match_teams {match_teams_id}")
                                    self.bracket_service.supabase.client.table('match_teams') \
                                        .update({'away': unpaired_team.team_id}) \
                                        .eq('id', match_teams_id) \
                                        .execute()
                                else:
                                    print(f"Error: Ambas posiciones (home y away) ya están ocupadas en match_teams {match_teams_id}")
                            else:
                                print(f"Error: No se pudo obtener información de match_teams {match_teams_id}")
                        else:
                            print(f"Error: No se encontró match_teams para el match {match_id}")
                    else:
                        print(f"Error: No se encontró match para el next_slot {unpaired_team.next_slot_id}")
                        
                    # Verificar que el equipo se haya asignado correctamente
                    verification = self.bracket_service.supabase.client.table('match') \
                        .select('*, match_teams(*)') \
                        .eq('id', match_id) \
                        .single() \
                        .execute()
                    
                    if verification.data and verification.data['match_teams']:
                        home = verification.data['match_teams'].get('home')
                        away = verification.data['match_teams'].get('away')
                        print(f"Verificación: Match {match_id} ahora tiene home={home}, away={away}")
                    else:
                        print(f"Error: No se pudo verificar la asignación del equipo {unpaired_team.team_id}")

            # Process unpaired teams
            self.bracket_service.process_unpaired_teams(unpaired_teams)

            # Create third place match if needed
            if has_third_place:
                print("Creando match por tercer lugar")
                final_stage = stages[-1]
                self.bracket_service.create_third_place_match(tournament_season_id, final_stage)

            print("Bracket creado exitosamente")
            return {
                'stages': stages,
                'slots': len(created_slots) + (1 if has_third_place else 0),
                'has_third_place': has_third_place
            }
        
        except Exception as error:
            print(f"Error in create_bracket_with_matches: {error}")
            raise 