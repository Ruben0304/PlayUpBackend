from http.client import HTTPException

from fastapi import APIRouter, Query, Request,UploadFile, File,Form

from domain.schemas.file_schema import ImageUploadRequest
from services.country_service import CountryService
from services.file_service import FileService
from services.notification_service import NotificationService
from services.tournament_season import TournamentSeasonService
from services.user_service import UserService

router = APIRouter()
file_service = FileService()


@router.get("/countries")
async def get_countries(language: str = "en"):
    return CountryService.get_countries(language)

@router.post("/tournament-season/handle-match-finished")
async def handle_match_finished(request: Request):
    payload = await request.json()
    return TournamentSeasonService.handle_match_finished(payload)

@router.post("/tournament-season/create-bracket")
async def create_bracket(request: Request):
    payload = await request.json()
    return TournamentSeasonService.create_bracket(payload)

@router.post("/tournament-season/update-standing-rank")
async def update_standing_rank(request: Request):
    payload = await request.json()
    return TournamentSeasonService.update_standing_rank(payload)

@router.post("/push-notification")
async def push_notification(request: Request):
    payload = await request.json()
    return NotificationService.push_notification(payload)

@router.post("/approve-organizer-from-waitlist")
async def approve_organizer_from_waitlist(request: Request):
    payload = await request.json()
    return UserService.approve_organizer_from_waitlist(payload['user_id'])

@router.post("/upload")
async def upload_file(
        folder_name: str = Form(...),
        target_width: int = Form(...),
        target_height: int = Form(...),
        desired_filename: str = Form(...),
        file: UploadFile = File(...)
):
    try:
        # Validar tipo de archivo
        if not file.content_type.startswith("image/"):
            raise HTTPException(400, "Solo se permiten archivos de imagen")

        # Crear request object
        upload_request = ImageUploadRequest(
            folder_name=folder_name,
            target_width=target_width,
            target_height=target_height,
            desired_filename=desired_filename
        )

        # Procesar y subir
        file_url = await file_service.process_and_upload(file, upload_request)

        return {"url": file_url}

    except Exception as e:
        raise HTTPException(500, f"Error subiendo archivo: {str(e)}")