from http.client import HTTPException

from fastapi import APIRouter, Query, Request,UploadFile, File,Form

from domain.schemas.file_schema import ImageUploadRequest
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi import APIRouter, Query, Request, HTTPException, File, UploadFile, Form, Depends
from services.country_service import CountryService
from services.file_service import FileService
from services.news_service import NewsService
from services.notification_service import NotificationService
from services.tournament_season import TournamentSeasonService
from services.user_service import UserService
from infrastructure.supabase_client import SupabaseClient
from services.news_interaction_service import NewsInteractionService
from typing import Optional, List
import json

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

@router.post("/news")
async def create_news(
    request: Request,
    title: str = Form(..., description="Título de la noticia"),
    body: str = Form(..., description="Contenido de la noticia"),
    media_files: List[UploadFile] = File([], description="Archivos multimedia (imágenes/videos)"),
    publisher_type: int = Form(..., description="Tipo de publicador (ID de user_type)")
):
    """
    Crea una nueva noticia.
    
    - Requiere autenticación
    - El usuario autenticado será el publicador si publisher_type=1 (user)
    - Soporta carga de múltiples archivos multimedia
    """
    try:
        # Obtener el user_id del token (requerido)
        user_id = await UserService.get_user_from_token(request, required=True)
        
        # Procesar los archivos multimedia
        media_data = []
        for media_file in media_files:
            # Leer el contenido del archivo
            content = await media_file.read()
            
            # Añadir a la lista de archivos
            media_data.append({
                "filename": media_file.filename,
                "content": content,
                "content_type": media_file.content_type
            })
        
        # Llamar al servicio para crear la noticia
        result = await NewsService.create_news(
            title=title,
            body=body,
            user_id=user_id,
            publisher_type=publisher_type,
            media_files=media_data
        )
        
        return result
        
    except HTTPException as http_ex:
        # Reenviar excepciones HTTP
        raise http_ex
    except Exception as e:
        print(f"Error al crear noticia: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al crear noticia: {str(e)}")

@router.delete("/news/{news_id}")
async def delete_news(news_id: int, request: Request):
    """
    Elimina una noticia.
    
    - Requiere autenticación
    - Solo el creador de la noticia o un administrador puede eliminarla
    """
    try:
        # Obtener el user_id del token (requerido)
        user_id = await UserService.get_user_from_token(request, required=True)
        
        # Llamar al servicio para eliminar la noticia
        result = NewsService.delete_news(news_id, user_id)
        
        return result
        
    except HTTPException as http_ex:
        # Reenviar excepciones HTTP
        raise http_ex
    except Exception as e:
        print(f"Error al eliminar noticia: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al eliminar noticia: {str(e)}")

@router.put("/news/{news_id}")
async def update_news(
    news_id: int,
    request: Request,
    title: str = Form(None, description="Título de la noticia"),
    body: str = Form(None, description="Contenido de la noticia"),
    media_files: List[UploadFile] = File([], description="Nuevos archivos multimedia (imágenes/videos)"),
    delete_media: str = Form("[]", description="URLs de archivos multimedia a eliminar en formato JSON array"),
    is_featured: bool = Form(None, description="Destacar la noticia"),
    is_breaking: bool = Form(None, description="Noticia de última hora")
):
    """
    Actualiza una noticia existente.
    
    - Requiere autenticación
    - Solo el creador de la noticia o un administrador puede actualizarla
    - Permite añadir nuevos archivos multimedia y eliminar existentes
    """
    try:
        # Obtener el user_id del token (requerido)
        user_id = await UserService.get_user_from_token(request, required=True)
        
        # Convertir delete_media de string JSON a lista
        media_to_delete = []
        if delete_media:
            try:
                media_to_delete = json.loads(delete_media)
                if not isinstance(media_to_delete, list):
                    media_to_delete = []
            except:
                media_to_delete = []
        
        # Procesar los nuevos archivos multimedia
        media_data = []
        for media_file in media_files:
            # Leer el contenido del archivo
            content = await media_file.read()
            
            # Añadir a la lista de archivos
            media_data.append({
                "filename": media_file.filename,
                "content": content,
                "content_type": media_file.content_type
            })
        
        # Llamar al servicio para actualizar la noticia
        result = await NewsService.update_news(
            news_id=news_id,
            user_id=user_id,
            title=title,
            body=body,
            new_media_files=media_data,
            delete_media_urls=media_to_delete,
            is_featured=is_featured,
            is_breaking=is_breaking
        )
        
        return result
        
    except HTTPException as http_ex:
        # Reenviar excepciones HTTP
        raise http_ex
    except Exception as e:
        print(f"Error al actualizar noticia: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al actualizar noticia: {str(e)}")

@router.get("/user/profiles")
async def get_user_profiles(request: Request):
    """
    Obtiene todos los perfiles con los que un usuario puede publicar:
    - Su perfil de usuario
    - Equipos que posee
    - Organizaciones a las que pertenece
    - Torneos que administra
    
    Cada perfil contiene:
    - id: ID del perfil
    - name: Nombre del perfil
    - image: URL de la imagen del perfil
    
    Requiere autenticación.
    """
    try:
        # Obtener el user_id del token (requerido)
        user_id = await UserService.get_user_from_token(request, required=True)
        
        # Obtener los perfiles del usuario
        profiles = UserService.get_user_profiles(user_id)
        
        # Devolver directamente la lista de perfiles sin envolverla en un objeto data
        return profiles
        
    except HTTPException as http_ex:
        # Reenviar excepciones HTTP
        raise http_ex
    except Exception as e:
        print(f"Error al obtener perfiles del usuario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al obtener perfiles del usuario: {str(e)}")

        