from domain.models import NewsModel
from infrastructure.supabase_client import SupabaseClient
from translations import COUNTRY_TRANSLATIONS
from services.news_interaction_service import NewsInteractionService
import uuid
import os
from datetime import datetime
from fastapi import HTTPException
from services.user_service import UserService

class NewsService:
    @staticmethod
    def fetch(page=1, page_size=20, user_id=None):
        try:
            # Calcular el rango para la paginación
            start = (page - 1) * page_size
            end = start + page_size - 1
            
            # Obtener el total de registros
            count_response = SupabaseClient.client.table('news').select('count', count='exact').execute()
            total = count_response.count if hasattr(count_response, 'count') else 0
            
            # Obtener los datos paginados
            response = SupabaseClient.client.table('news').select('*').order('created_at', desc=True).range(start, end).execute()
            data = response.data
            
            # Obtener los datos de user_type
            user_types_response = SupabaseClient.client.table('user_type').select('*').execute()
            user_types = {ut['id']: ut['name'] for ut in user_types_response.data}
            
            # Mapeo de campos de imagen por tipo de publisher
            image_field_map = {
                'user': 'avatar_url',
                'organization': 'logo',
                'team': 'logo',
                'tournament': 'logo'
            }
            
            # Mapeo de campos de nombre por tipo de publisher
            name_field_map = {
                'user': 'username',
                'organization': 'name',
                'team': 'name',
                'tournament': 'name'
            }
            
            # Procesar los datos
            processed_data = []
            for item in data:
                # Crear una copia del item para no modificar el original
                processed_item = dict(item)
                
                # Obtener el tipo de publisher y su ID
                publisher_type_id = processed_item.get('publisher_type')
                publisher_id = processed_item.get('publisher')
                
                # Verificar que tenemos los datos necesarios
                if publisher_type_id is not None and publisher_id and publisher_type_id in user_types:
                    publisher_type_name = user_types[publisher_type_id]
                    
                    try:
                        # Determinar la tabla a consultar según el tipo
                        publisher_table = publisher_type_name  # user, organization, team, tournament
                        
                        # Determinar el campo de imagen según el tipo
                        image_field = image_field_map.get(publisher_type_name, 'image')
                        
                        # Determinar el campo de nombre según el tipo
                        name_field = name_field_map.get(publisher_type_name, 'name')
                        
                        # Construir la consulta para seleccionar los campos correctos
                        fields = f"id,{name_field},{image_field}"
                        
                        # Consulta para obtener los datos del publisher
                        pub_response = SupabaseClient.client.table(publisher_table).select(fields).eq('id', publisher_id).execute()
                        
                        if pub_response.data and len(pub_response.data) > 0:
                            pub_data = pub_response.data[0]
                            
                            # Reemplazar el ID con un objeto que contiene id, name e image
                            # Asegurarse de que el ID sea siempre un string
                            processed_item['publisher'] = {
                                'id': str(pub_data['id']),
                                'name': pub_data.get(name_field, ''),
                                'image': pub_data.get(image_field, '')
                            }
                        else:
                            # Valor predeterminado si no se encuentra
                            processed_item['publisher'] = {
                                'id': str(publisher_id),
                                'name': f"Publisher {publisher_id}",
                                'image': ""
                            }
                    except Exception as pub_error:
                        print(f"Error al obtener publisher {publisher_id} de tipo {publisher_type_name}: {pub_error}")
                        # Establecer un valor predeterminado para publisher
                        processed_item['publisher'] = {
                            'id': str(publisher_id),
                            'name': f"Publisher {publisher_id}",
                            'image': ""
                        }
                else:
                    # Valor predeterminado si faltan datos
                    if publisher_id:
                        processed_item['publisher'] = {
                            'id': str(publisher_id),
                            'name': f"Publisher {publisher_id}",
                            'image': ""
                        }
                
                # Añadir conteos de likes y comentarios
                news_id = processed_item['id']
                processed_item['like_count'] = NewsInteractionService.get_like_count(news_id)
                processed_item['comment_count'] = NewsInteractionService.get_comment_count(news_id)
                
                # Si se proporciona un user_id, verificar si el usuario ha dado like
                if user_id:
                    processed_item['user_liked'] = NewsInteractionService.has_user_liked(news_id, user_id)
                
                processed_data.append(processed_item)
            
        except Exception as e:
            print(f"Error general: {e}")
            return {"error": str(e), "data": [], "total": 0, "limit": page_size, "page": page}

        return {"data": processed_data, "total": total, "limit": page_size, "page": page}

    @staticmethod
    def fetch_by_id(news_id, user_id=None):
        """
        Obtener una noticia específica por su ID
        
        Args:
            news_id: ID de la noticia
            user_id: ID del usuario (opcional, para verificar si ha dado like)
            
        Returns:
            Diccionario con los datos de la noticia
        """
        try:
            # Obtener la noticia
            response = SupabaseClient.client.table('news').select('*').eq('id', news_id).single().execute()
            
            if not response.data:
                return {"error": "Noticia no encontrada"}
            
            # Procesar la noticia (mismo código que en fetch)
            processed_item = dict(response.data)
            
            # Obtener el tipo de publisher y su ID
            publisher_type_id = processed_item.get('publisher_type')
            publisher_id = processed_item.get('publisher')
            
            # Obtener los datos de user_type
            user_types_response = SupabaseClient.client.table('user_type').select('*').execute()
            user_types = {ut['id']: ut['name'] for ut in user_types_response.data}
            
            # Mapeo de campos
            image_field_map = {
                'user': 'avatar_url',
                'organization': 'logo',
                'team': 'logo',
                'tournament': 'logo'
            }
            
            name_field_map = {
                'user': 'username',
                'organization': 'name',
                'team': 'name',
                'tournament': 'name'
            }
            
            # Procesar publisher
            if publisher_type_id is not None and publisher_id and publisher_type_id in user_types:
                publisher_type_name = user_types[publisher_type_id]
                
                try:
                    # Consultar datos del publisher
                    publisher_table = publisher_type_name
                    image_field = image_field_map.get(publisher_type_name, 'image')
                    name_field = name_field_map.get(publisher_type_name, 'name')
                    
                    fields = f"id,{name_field},{image_field}"
                    
                    pub_response = SupabaseClient.client.table(publisher_table).select(fields).eq('id', publisher_id).execute()
                    
                    if pub_response.data and len(pub_response.data) > 0:
                        pub_data = pub_response.data[0]
                        processed_item['publisher'] = {
                            'id': str(pub_data['id']),
                            'name': pub_data.get(name_field, ''),
                            'image': pub_data.get(image_field, '')
                        }
                    else:
                        processed_item['publisher'] = {
                            'id': str(publisher_id),
                            'name': f"Publisher {publisher_id}",
                            'image': ""
                        }
                except Exception as pub_error:
                    print(f"Error al obtener publisher: {pub_error}")
                    processed_item['publisher'] = {
                        'id': str(publisher_id),
                        'name': f"Publisher {publisher_id}",
                        'image': ""
                    }
            elif publisher_id:
                processed_item['publisher'] = {
                    'id': str(publisher_id),
                    'name': f"Publisher {publisher_id}",
                    'image': ""
                }
            
            # Añadir conteos de likes y comentarios
            processed_item['like_count'] = NewsInteractionService.get_like_count(news_id)
            processed_item['comment_count'] = NewsInteractionService.get_comment_count(news_id)
            
            # Si se proporciona un user_id, verificar si el usuario ha dado like
            if user_id:
                processed_item['user_liked'] = NewsInteractionService.has_user_liked(news_id, user_id)
            
            return {"data": processed_item}
            
        except Exception as e:
            print(f"Error al obtener noticia: {e}")
            return {"error": str(e)}

    @staticmethod
    async def create_news(title, body, user_id, publisher_type, publisher_id=None, media_files=None, media_urls=None):
        """
        Crea una nueva noticia.
        
        Args:
            title: Título de la noticia
            body: Contenido de la noticia
            user_id: ID del usuario que crea la noticia
            publisher_type: Tipo de publicador (ID de user_type)
            publisher_id: ID del publicador (opcional, requerido si publisher_type != 1)
            media_files: Lista de diccionarios con datos de archivos multimedia (opcional)
            media_urls: Lista de URLs de archivos multimedia ya procesados (opcional)
            
        Returns:
            Diccionario con los datos de la noticia creada
        """
        try:
            # Obtener el tipo de publicador de la tabla user_type
            user_type_response = SupabaseClient.client.table('user_type').select('name').eq('id', publisher_type).single().execute()
            
            if not user_type_response.data:
                raise HTTPException(status_code=400, detail=f"Tipo de publicador inválido: {publisher_type}")
            
            publisher_type_name = user_type_response.data.get('name')
            
            # Determinar el publisher_id basado en el publisher_type
            final_publisher_id = None
            
            # Si el publisher_type es 'user', el publisher es el usuario actual por defecto
            if publisher_type_name == 'user':
                final_publisher_id = publisher_id if publisher_id else user_id
            else:
                # Para otros tipos (organización, equipo, torneo), se requiere el publisher_id
                if not publisher_id:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Para publisher_type '{publisher_type_name}', se debe especificar el publisher_id"
                    )
                final_publisher_id = publisher_id
            
            # Verificar que el publisher existe en la tabla correspondiente
            try:
                publisher_response = SupabaseClient.client.table(publisher_type_name).select('id').eq('id', final_publisher_id).single().execute()
                
                if not publisher_response.data:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"El publicador con ID {final_publisher_id} no existe en la tabla {publisher_type_name}"
                    )
                
                # Verificar que el usuario tiene permisos para publicar como este publisher
                if publisher_type_name != 'user' or (publisher_type_name == 'user' and str(final_publisher_id) != str(user_id)):
                    # Verificar permisos según el tipo de publisher
                    has_permission = False
                    
                    if publisher_type_name == 'team':
                        # Verificar si el usuario es dueño del equipo
                        team_response = SupabaseClient.client.table('team').select('user').eq('id', final_publisher_id).single().execute()
                        has_permission = team_response.data and str(team_response.data.get('user')) == str(user_id)
                    
                    elif publisher_type_name == 'organization':
                        # Verificar si el usuario pertenece a la organización
                        org_response = SupabaseClient.client.table('user_organization').select('id').eq('organization', final_publisher_id).eq('user', user_id).execute()
                        has_permission = org_response.data and len(org_response.data) > 0
                    
                    elif publisher_type_name == 'tournament':
                        # Verificar si el usuario está asociado al torneo a través de la organización
                        tournament_response = SupabaseClient.client.table('tournament').select('organization').eq('id', final_publisher_id).single().execute()
                        if tournament_response.data:
                            org_id = tournament_response.data.get('organization')
                            org_response = SupabaseClient.client.table('user_organization').select('id').eq('organization', org_id).eq('user', user_id).execute()
                            has_permission = org_response.data and len(org_response.data) > 0
                    
                    if not has_permission:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"No tienes permisos para publicar como este {publisher_type_name}"
                        )
            
            except HTTPException as http_ex:
                raise http_ex
            except Exception as e:
                print(f"Error al verificar publisher: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Error al verificar publisher: {str(e)}"
                )
            
            # Subir los archivos multimedia si se proporcionan
            final_media_urls = []
            
            # Si se proporcionan URLs ya procesadas, usarlas directamente
            if media_urls:
                final_media_urls = media_urls
            # Si no, procesar los archivos multimedia si se proporcionan
            elif media_files:
                # Asegurarse de que el bucket existe
                bucket_name = "news_media"
                try:
                    buckets = SupabaseClient.client.storage.list_buckets()
                    bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
                    
                    if not bucket_exists:
                        SupabaseClient.client.storage.create_bucket(bucket_name)
                except Exception as bucket_error:
                    print(f"Error al verificar/crear bucket: {bucket_error}")
                
                # Subir cada archivo
                for media_file in media_files:
                    try:
                        # Generar un nombre único para el archivo
                        file_ext = os.path.splitext(media_file.get('filename', ''))[1]
                        unique_filename = f"{uuid.uuid4()}{file_ext}"
                        file_path = f"{unique_filename}"
                        
                        # Subir el archivo
                        result = SupabaseClient.client.storage.from_(bucket_name).upload(
                            file_path,
                            media_file.get('content'),
                            file_options={"content-type": media_file.get('content_type', 'image/jpeg')}
                        )
                        
                        # Obtener la URL pública
                        media_url = SupabaseClient.client.storage.from_(bucket_name).get_public_url(file_path)
                        final_media_urls.append(media_url)
                    except Exception as upload_error:
                        print(f"Error al subir archivo multimedia: {upload_error}")
            
            # Preparar datos para la inserción
            news_data = {
                'title': title,
                'body': body,
                'publisher_type': publisher_type,
                'publisher': str(final_publisher_id),  # Asegurarse de que sea string según la estructura
                'media_urls': final_media_urls,  # Array de URLs
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Insertar la noticia
            news_response = SupabaseClient.client.table('news').insert(news_data).execute()
            
            if not news_response.data:
                raise Exception("No se pudo crear la noticia")
            
            news_id = news_response.data[0].get('id')
            
            # Obtener la noticia completa con el mismo formato que fetch_by_id
            return NewsService.fetch_by_id(news_id, user_id)
            
        except HTTPException as http_ex:
            raise http_ex
        except Exception as e:
            print(f"Error al crear noticia: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error al crear noticia: {str(e)}")

    @staticmethod
    def delete_news(news_id, user_id):
        """
        Elimina una noticia.
        
        Args:
            news_id: ID de la noticia a eliminar
            user_id: ID del usuario que intenta eliminar la noticia
            
        Returns:
            Diccionario con el resultado de la operación
        """
        try:
            # Verificar que la noticia existe y que el usuario tiene permisos para eliminarla
            news = SupabaseClient.client.table('news').select('publisher, publisher_type').eq('id', news_id).single().execute()
            
            if not news.data:
                raise HTTPException(status_code=404, detail="Noticia no encontrada")
            
            # Verificar si el usuario es el creador de la noticia
            publisher = news.data.get('publisher')
            publisher_type = news.data.get('publisher_type')
            
            # Si el publisher_type es 1 (user) y el publisher es el usuario actual, o si el usuario es admin
            is_creator = publisher_type == 1 and publisher == str(user_id)
            is_admin = UserService.is_admin(user_id)  # Asumiendo que existe este método
            
            if not (is_creator or is_admin):
                raise HTTPException(status_code=403, detail="No tienes permisos para eliminar esta noticia")
            
            # Eliminar archivos multimedia asociados
            if 'media_urls' in news.data and news.data['media_urls']:
                bucket_name = "news_media"
                for url in news.data['media_urls']:
                    try:
                        # Extraer el nombre del archivo de la URL
                        file_name = url.split('/')[-1]
                        SupabaseClient.client.storage.from_(bucket_name).remove([file_name])
                    except Exception as e:
                        print(f"Error al eliminar archivo multimedia: {e}")
            
            # Eliminar la noticia
            SupabaseClient.client.table('news').delete().eq('id', news_id).execute()
            
            return {"success": True, "message": "Noticia eliminada correctamente"}
            
        except HTTPException as http_ex:
            raise http_ex
        except Exception as e:
            print(f"Error al eliminar noticia: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error al eliminar noticia: {str(e)}")

    @staticmethod
    async def update_news(news_id, user_id, title=None, body=None, new_media_files=None, delete_media_urls=None, is_featured=None, is_breaking=None):
        """
        Actualiza una noticia existente.
        
        Args:
            news_id: ID de la noticia a actualizar
            user_id: ID del usuario que intenta actualizar la noticia
            title: Nuevo título (opcional)
            body: Nuevo contenido (opcional)
            new_media_files: Nuevos archivos multimedia (opcional)
            delete_media_urls: URLs de archivos multimedia a eliminar (opcional)
            is_featured: Si la noticia es destacada (opcional)
            is_breaking: Si la noticia es de última hora (opcional)
            
        Returns:
            Diccionario con los datos de la noticia actualizada
        """
        try:
            # Verificar que la noticia existe y que el usuario tiene permisos para actualizarla
            news_response = SupabaseClient.client.table('news').select('*').eq('id', news_id).single().execute()
            
            if not news_response.data:
                raise HTTPException(status_code=404, detail="Noticia no encontrada")
            
            news = news_response.data
            
            # Verificar si el usuario es el creador de la noticia
            publisher = news.get('publisher')
            publisher_type = news.get('publisher_type')
            
            # Si el publisher_type es 1 (user) y el publisher es el usuario actual, o si el usuario es admin
            is_creator = publisher_type == 1 and publisher == str(user_id)
            is_admin = UserService.is_admin(user_id)  # Asumiendo que existe este método
            
            if not (is_creator or is_admin):
                raise HTTPException(status_code=403, detail="No tienes permisos para actualizar esta noticia")
            
            # Preparar datos para la actualización
            update_data = {}
            
            if title is not None:
                update_data['title'] = title
            
            if body is not None:
                update_data['body'] = body
            
            if is_featured is not None:
                update_data['is_featured'] = is_featured
            
            if is_breaking is not None:
                update_data['is_breaking'] = is_breaking
            
            # Actualizar la fecha de modificación
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Gestionar archivos multimedia
            current_media_urls = news.get('media_urls', [])
            
            # Eliminar archivos multimedia si se solicita
            if delete_media_urls:
                bucket_name = "news_media"
                for url in delete_media_urls:
                    if url in current_media_urls:
                        try:
                            # Extraer el nombre del archivo de la URL
                            file_name = url.split('/')[-1]
                            SupabaseClient.client.storage.from_(bucket_name).remove([file_name])
                            current_media_urls.remove(url)
                        except Exception as e:
                            print(f"Error al eliminar archivo multimedia: {e}")
            
            # Añadir nuevos archivos multimedia
            if new_media_files:
                bucket_name = "news_media"
                
                # Asegurarse de que el bucket existe
                try:
                    buckets = SupabaseClient.client.storage.list_buckets()
                    bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
                    
                    if not bucket_exists:
                        SupabaseClient.client.storage.create_bucket(bucket_name)
                except Exception as bucket_error:
                    print(f"Error al verificar/crear bucket: {bucket_error}")
                
                # Subir cada archivo
                for media_file in new_media_files:
                    try:
                        # Generar un nombre único para el archivo
                        file_ext = os.path.splitext(media_file.get('filename', ''))[1]
                        unique_filename = f"{uuid.uuid4()}{file_ext}"
                        file_path = f"{unique_filename}"
                        
                        # Subir el archivo
                        result = SupabaseClient.client.storage.from_(bucket_name).upload(
                            file_path,
                            media_file.get('content'),
                            file_options={"content-type": media_file.get('content_type', 'image/jpeg')}
                        )
                        
                        # Obtener la URL pública
                        media_url = SupabaseClient.client.storage.from_(bucket_name).get_public_url(file_path)
                        current_media_urls.append(media_url)
                    except Exception as upload_error:
                        print(f"Error al subir archivo multimedia: {upload_error}")
            
            # Actualizar la lista de URLs de archivos multimedia
            update_data['media_urls'] = current_media_urls
            
            # Actualizar la noticia
            if update_data:
                SupabaseClient.client.table('news').update(update_data).eq('id', news_id).execute()
            
            # Obtener la noticia actualizada
            return NewsService.fetch_by_id(news_id, user_id)
            
        except HTTPException as http_ex:
            raise http_ex
        except Exception as e:
            print(f"Error al actualizar noticia: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Error al actualizar noticia: {str(e)}")
