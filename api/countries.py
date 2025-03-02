from fastapi import APIRouter, Query
from services.country_service import CountryService

router = APIRouter()

@router.get("/countries")
async def get_countries(language: str = "en"):
    return CountryService.get_countries(language)
