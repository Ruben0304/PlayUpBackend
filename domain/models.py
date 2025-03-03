from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Union

# Base config for all models that need number to string coercion
model_config = ConfigDict(coerce_numbers_to_str=True)

class Country(BaseModel):
    code: str
    name: str

class Goals(BaseModel):
    home: int
    away: int

class Stage(BaseModel):
    model_config = model_config
    id: str
    name: str

class FixtureRound(BaseModel):
    model_config = model_config
    id: str
    round: str
    stage: Stage

class MatchTeams(BaseModel):
    model_config = model_config
    id: str
    home: Optional[str] = None
    away: Optional[str] = None

class BracketSlot:
    def __init__(self, id: int, next_slot: int = None):
        self.id = id
        self.next_slot = next_slot

class Match:
    def __init__(self, id: int, goals: Goals, match_teams: MatchTeams, 
                 tournament_season: int, fixture_round: FixtureRound, 
                 bracket_slot: BracketSlot):
        self.id = id
        self.goals = Goals(**goals)
        self.match_teams = MatchTeams(**match_teams)
        self.tournament_season = tournament_season
        self.fixture_round = FixtureRound(**fixture_round)
        # Tomamos el primer bracket_slot si existe
        self.bracket_slot = BracketSlot(**bracket_slot)

class TournamentDoubleRound(BaseModel):
    elimination: bool
    group_stage: bool
    round_robin: bool

class TournamentSeason(BaseModel):
    model_config = model_config
    tournament_double_round: TournamentDoubleRound

class OtherMatch(BaseModel):
    model_config = model_config
    id: str
    goals: Goals
    match_teams: MatchTeams
