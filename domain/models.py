from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Union, Dict, Any
from dataclasses import dataclass

# Base config for all models that need number to string coercion
model_config = ConfigDict(coerce_numbers_to_str=True)

class Country(BaseModel):
    code: str
    name: str

class Goals(BaseModel):
    home: Optional[int]
    away: Optional[int]

class Stage(BaseModel):
    model_config = model_config
    id: int
    name: str

class FixtureRound(BaseModel):
    model_config = model_config
    id: int
    round: str
    stage: Stage

class MatchTeams(BaseModel):
    model_config = model_config
    id: int
    home: Optional[int]
    away: Optional[int]

class BracketSlot:
    def __init__(self, id: int, next_slot: Optional[int] = None):
        self.id = id
        self.next_slot = next_slot

class Match:
    def __init__(self, id: int, goals: Goals, match_teams: MatchTeams, 
                 tournament_season: int, fixture_round: FixtureRound, 
                 bracket_slot: Optional[BracketSlot] = None):
        self.id = id
        self.goals = Goals(**goals)
        self.match_teams = MatchTeams(**match_teams)
        self.tournament_season = tournament_season
        self.fixture_round = FixtureRound(**fixture_round)
        self.bracket_slot = BracketSlot(**bracket_slot) if bracket_slot else None

class TournamentDoubleRound(BaseModel):
    elimination: bool
    group_stage: bool
    round_robin: bool

@dataclass
class TournamentStructure:
    has_third_place: bool

class TournamentSeason(BaseModel):
    model_config = model_config
    id: Optional[int] = None
    tournament: Optional[int] = None
    season: Optional[Any] = None
    current: Optional[bool] = None
    banner_image: Optional[str] = None
    created_at: Optional[str] = None
    description: Optional[str] = None
    game: Optional[Any] = None
    start_date: Optional[str] = None
    total_fixtures: Optional[int] = None
    tournament_prize: Optional[Any] = None
    tournament_rule: Optional[Any] = None
    tournament_status: Optional[Any] = None
    tournament_mode: Optional[Any] = None
    tournament_structure: Optional[TournamentStructure] = None
    access_config: Optional[Any] = None
    tournament_double_round: Optional[TournamentDoubleRound] = None

class OtherMatch(BaseModel):
    model_config = model_config
    id: str
    goals: Goals
    match_teams: MatchTeams

@dataclass
class UnpairedTeam:
    team_id: int
    next_slot_id: int

@dataclass
class MatchTeams:
    id: int
    home: Optional[int]
    away: Optional[int]

@dataclass
class BracketStage:
    id: int
    tournament_season: int
    fixture_round: int
