from fastapi import APIRouter, Query, Request
from services.country_service import CountryService
from services.tournament_season import TournamentSeasonService


router = APIRouter()

@router.get("/countries")
async def get_countries(language: str = "en"):
    return CountryService.get_countries(language)

@router.post("/tournament-seasons/handle-match-finished")
async def handle_match_finished(request: Request):
    payload = await request.json()
    return TournamentSeasonService.handle_match_finished(payload)
