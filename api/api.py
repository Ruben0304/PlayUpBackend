from http.client import HTTPException

from fastapi import APIRouter, Query, Request,UploadFile, File,Form

from domain.schemas.file_schema import ImageUploadRequest
from fastapi import APIRouter, Query, Request, HTTPException
from services.country_service import CountryService
from services.file_service import FileService
from services.news_service import NewsService
from services.notification_service import NotificationService
from services.tournament_season import TournamentSeasonService
from services.user_service import UserService
from infrastructure.supabase_client import SupabaseClient
from services.news_interaction_service import NewsInteractionService

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
    # Verificar que el usuario actual tiene permisos para aprobar organizadores
    admin_id = await UserService.get_user_from_token(request, required=True)
    
    # Obtener el ID del usuario a aprobar
    payload = await request.json()
    user_id_to_approve = payload.get('user_id')
    
    if not user_id_to_approve:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    return UserService.approve_organizer_from_waitlist(user_id_to_approve)

@router.get("/news")
async def get_news(request: Request, page: int = 1, page_size: int = 20):
    user_id = await UserService.get_user_from_token(request)
    return NewsService.fetch(page, page_size, user_id)

@router.post("/news/{news_id}/like")
async def toggle_like(news_id: int, request: Request):
    user_id = await UserService.get_user_from_token(request, required=True)
    return NewsInteractionService.toggle_like(news_id, user_id)

@router.post("/news/{news_id}/comment")
async def add_comment(news_id: int, request: Request):
    # Obtener el user_id del token (requerido)
    user_id = await UserService.get_user_from_token(request, required=True)
    
    # Obtener el contenido del comentario
    payload = await request.json()
    content = payload.get("content")
    
    if not content:
        raise HTTPException(status_code=400, detail="Comment content is required")
    
    return NewsInteractionService.add_comment(news_id, user_id, content)

@router.get("/news/{news_id}/comments")
async def get_comments(
    news_id: int, 
    page: int = Query(1, ge=1, description="Número de página, comenzando desde 1"),
    page_size: int = Query(10, ge=1, le=50, description="Número de comentarios por página (máx. 50)")
):
    """
    Obtiene los comentarios de una noticia específica con paginación.
    
    - **news_id**: ID de la noticia
    - **page**: Número de página (comienza en 1)
    - **page_size**: Número de comentarios por página (máximo 50)
    
    Devuelve los comentarios ordenados por fecha de creación (más recientes primero)
    con información del usuario que los publicó.
    """
    return NewsInteractionService.get_comments(news_id, page, page_size)

@router.delete("/news/comment/{comment_id}")
async def delete_comment(comment_id: int, request: Request):
    # Obtener el user_id del token (requerido)
    user_id = await UserService.get_user_from_token(request, required=True)
    return NewsInteractionService.delete_comment(comment_id, user_id)

@router.get("/news/{news_id}")
async def get_news_detail(
    news_id: int, 
    request: Request, 
    include_comments: bool = Query(False, description="Incluir comentarios en la respuesta"),
    comments_page: int = Query(1, ge=1, description="Página de comentarios"),
    comments_page_size: int = Query(10, ge=1, le=50, description="Comentarios por página")
):
    """
    Obtiene una noticia específica con detalles completos.
    
    Opcionalmente puede incluir los comentarios de la noticia.
    """
    user_id = await UserService.get_user_from_token(request)
    
    # Obtener la noticia
    news_detail = NewsService.fetch_by_id(news_id, user_id)
    
    # Si se solicitan comentarios, incluirlos en la respuesta
    if include_comments and news_detail and "data" in news_detail:
        comments = NewsInteractionService.get_comments(news_id, comments_page, comments_page_size)
        news_detail["comments"] = comments
    
    return news_detail

@router.get("/debug/news/{news_id}/comments")
async def debug_comments(news_id: int):
    """
    Endpoint de diagnóstico para verificar comentarios directamente.
    """
    try:
        # Consulta directa a la base de datos
        response = SupabaseClient.client.table('news_comment').select('*').eq('news_id', news_id).execute()
        
        # Verificar si hay datos
        if hasattr(response, 'data'):
            return {
                "raw_data": response.data,
                "count": len(response.data) if response.data else 0,
                "news_id": news_id
            }
        else:
            return {"error": "No se pudo obtener datos", "response": str(response)}
    except Exception as e:
        return {"error": str(e)}

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