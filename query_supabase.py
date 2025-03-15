# Define QueryProperty before using it
class QueryProperty:
    """Descriptor para propiedades de consulta que resuelve referencias automáticamente"""
    def __init__(self, value):
        self.value = value
    
    def __get__(self, obj, objtype=None):
        import re
        query_string = self.value
        
        # Busca patrones como 'property(property)' o 'property!inner(property)'
        pattern = r'(\w+)(!inner)?\((\w+)\)'
        
        def replace_ref(match):
            full_match = match.group(0)
            prefix = match.group(1)
            inner = match.group(2) or ""
            ref_name = match.group(3)
            
            # Si la referencia existe como propiedad de la clase
            if hasattr(objtype, ref_name):
                ref_value = getattr(objtype, ref_name)
                # Si el valor de referencia es un descriptor, obtenemos su valor
                if isinstance(ref_value, QueryProperty):
                    ref_value = ref_value.value
                return f"{prefix}{inner}({ref_value})"
            return full_match
        
        # Reemplaza todas las referencias encontradas
        resolved = re.sub(pattern, replace_ref, query_string)
        return resolved

# This class contains all tables inside of supabase database
class QuerySupabase:
    @classmethod
    def _resolve_references(cls, query_string):
        """Resuelve referencias a otras propiedades en la cadena de consulta"""
        import re
        # Busca patrones como 'property(property)' o 'property!inner(property)'
        pattern = r'(\w+)(!inner)?\((\w+)\)'
        
        def replace_ref(match):
            full_match = match.group(0)
            prefix = match.group(1)
            inner = match.group(2) or ""
            ref_name = match.group(3)
            
            # Si la referencia existe como propiedad de la clase
            if hasattr(cls, ref_name):
                return f"{prefix}{inner}({getattr(cls, ref_name)})"
            return full_match
        
        # Reemplaza todas las referencias encontradas
        resolved = re.sub(pattern, replace_ref, query_string)
        return resolved
    
    @classmethod
    def get(cls, attr_name):
        """Obtiene una propiedad y resuelve sus referencias"""
        if hasattr(cls, attr_name):
            value = getattr(cls, attr_name)
            return cls._resolve_references(value)
        return None
    
    # Definiciones básicas
    user = QueryProperty("id, username, avatar_url, updated_at, first_name, last_name, country(country), gender(gender), birthdate")
    gender = QueryProperty("id, name")
    role = QueryProperty("id, name")
    permission = QueryProperty("id, name")
    matchStatus = QueryProperty("id, long, short")
    organization = QueryProperty("id, name, logo")
    country = QueryProperty("id, name, code, flag")
    goals = QueryProperty("id, home, away")
    fixtureRound = QueryProperty("id, round")
    season = QueryProperty("id, name")
    group = QueryProperty("id, name")
    game = QueryProperty("id, name")
    tournamentMode = QueryProperty("id, name")
    playerPosition = QueryProperty("id, name")
    event = QueryProperty("id, event_type, type")
    notification = QueryProperty("id, title, body, is_read, created_at")
    
    # Definiciones con referencias
    status = QueryProperty("id, elapsed, match_status(matchStatus)")
    tournament = QueryProperty("id, created_at, name, description, logo, banner_image, organization(organization)")
    tournamentRules = QueryProperty("id, updated_at, max_players, min_players, description")
    tournamentPrize = QueryProperty("id, prizepool, first_place, second_place, third_place")
    tournamentStatus = QueryProperty("id, status")
    tournamentDoubleRound = QueryProperty("id, group_stage, elimination, round_robin")
    tournamentAccessConfig = QueryProperty("id, name, is_private, requires_approval")
    tournamentStructure = QueryProperty("id, max_teams, group_size, winners_per_group, promotion_total, relegation_total, has_third_place")
    userRole = QueryProperty("id, user(user), role(role)")
    team = QueryProperty("id, created_at, name, logo, location, code, user(user)")
    player = QueryProperty("id, name, first_name, preferred_foot, image, birthdate, identification, height, weight, position, country(country), user(user)")
    matchTeams = QueryProperty("id, home(team), away(team)")
    bookmarkRoster = QueryProperty("id, player(player), player_position(playerPosition), number")
    userOrganization = QueryProperty("id, user(user), organization(organization)")
    appInfo = QueryProperty("id, created_at, force_update, build_number, version, description, link")
    organizerWaitlist = QueryProperty("id, user(user)")
    playerStats = QueryProperty("id, goals, assists, yellow_cards, red_cards, player(player), team(team)")
    standing = QueryProperty("id, rank, points, goals_diff, goals_f, goals_c, form, status, description, updated_at, group(group)")
    tournamentSeason = QueryProperty("id, current, start_date, created_at, total_fixtures, banner_image, description, is_group_generated, is_matchs_generated, season(season), tournament(tournament), current_round(fixtureRound), tournament_rule(tournamentRules), tournament_prize(tournamentPrize), tournament_status(tournamentStatus), game(game), tournament_mode(tournamentMode), tournament_structure(tournamentStructure), tournament_double_round(tournamentDoubleRound), access_config(tournamentAccessConfig)")
    team_tournament = QueryProperty("id, in_competition, team(team), tournament_season(tournamentSeason), standing(standing)")
    match = QueryProperty("id, referee, date, time, location, tournament_season(tournamentSeason), status(status), match_teams(matchTeams), goals(goals), fixture_round(fixtureRound)")
    matchEvent = QueryProperty("id, time, match(match), roster(roster), event(*), assist(roster)")
    roster = QueryProperty("id, player(player), team_tournament(team_tournament), player_position(playerPosition), number, is_active")

# eventType = "id, type" 