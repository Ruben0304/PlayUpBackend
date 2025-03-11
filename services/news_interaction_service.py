from infrastructure.supabase_client import SupabaseClient

class NewsInteractionService:
    @staticmethod
    def toggle_like(news_id, user_id):
        """
        Añadir o quitar like de un usuario a una noticia.
        Devuelve true si el usuario tiene un like activo después de la operación,
        false si no tiene like activo.
        """
        try:
            # Verificar si ya existe un like de este usuario para esta noticia
            existing = SupabaseClient.client.table('news_like').select('id') \
                .eq('news_id', news_id) \
                .eq('user_id', user_id) \
                .execute()
            
            has_like = False
            
            if existing.data and len(existing.data) > 0:
                # Quitar like existente
                SupabaseClient.client.table('news_like').delete() \
                    .eq('id', existing.data[0]['id']).execute()
                has_like = False
            else:
                # Crear nuevo like
                SupabaseClient.client.table('news_like').insert({
                    'news_id': news_id,
                    'user_id': user_id
                }).execute()
                has_like = True
            
            return has_like
            
        except Exception as e:
            print(f"Error al gestionar like: {e}")
            # En caso de error, devolvemos el estado actual del like
            return NewsInteractionService.has_user_liked(news_id, user_id)
    
    @staticmethod
    def get_like_count(news_id):
        try:
            response = SupabaseClient.client.table('news_like').select(
                'count', count='exact'
            ).eq('news_id', news_id).execute()
            
            return response.count if hasattr(response, 'count') else 0
            
        except Exception as e:
            print(f"Error al obtener conteo de likes: {e}")
            return 0
    
    @staticmethod
    def has_user_liked(news_id, user_id):
        try:
            response = SupabaseClient.client.table('news_like').select('id') \
                .eq('news_id', news_id) \
                .eq('user_id', user_id) \
                .execute()
            
            return len(response.data) > 0
            
        except Exception as e:
            print(f"Error al verificar like de usuario: {e}")
            return False
    
    @staticmethod
    def add_comment(news_id, user_id, content):
        try:
            response = SupabaseClient.client.table('news_comment').insert({
                'news_id': news_id,
                'user_id': user_id,
                'content': content
            }).execute()
            
            count = NewsInteractionService.get_comment_count(news_id)
            
            return {
                "comment": response.data[0] if response.data else None,
                "comment_count": count,
                "news_id": news_id
            }
            
        except Exception as e:
            print(f"Error al añadir comentario: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_comments(news_id, page=1, page_size=10):
        """
        Obtener comentarios para una noticia con paginación.
        
        Args:
            news_id: ID de la noticia
            page: Número de página (comienza en 1)
            page_size: Número de comentarios por página
            
        Returns:
            Diccionario con comentarios paginados y metadatos
        """
        try:
            # Validar parámetros
            page = max(1, page)
            page_size = min(max(1, page_size), 50)
            
            # Calcular el offset para la paginación
            start = (page - 1) * page_size
            end = start + page_size - 1
            
            # Imprimir para depuración
            print(f"Buscando comentarios para news_id={news_id}, page={page}, page_size={page_size}")
            
            # Obtener comentarios directamente con Supabase
            comments_response = SupabaseClient.client.table('news_comment') \
                .select('id, content, created_at, user_id') \
                .eq('news_id', news_id) \
                .order('created_at', desc=True) \
                .range(start, end) \
                .execute()
            
            # Imprimir respuesta para depuración
            print(f"Respuesta de comentarios: {comments_response}")
            
            # Obtener el conteo total
            count_response = SupabaseClient.client.table('news_comment') \
                .select('count', count='exact') \
                .eq('news_id', news_id) \
                .execute()
            
            total = count_response.count if hasattr(count_response, 'count') else 0
            print(f"Total de comentarios: {total}")
            
            # Formatear los datos para incluir el objeto user
            comments = []
            if hasattr(comments_response, 'data') and comments_response.data:
                # Obtener todos los user_ids únicos
                user_ids = list(set(comment.get('user_id') for comment in comments_response.data if isinstance(comment, dict)))
                
                # Obtener información de usuarios en una sola consulta
                users_data = {}
                if user_ids:
                    users_response = SupabaseClient.client.table('user') \
                        .select('id, username, avatar_url') \
                        .in_('id', user_ids) \
                        .execute()
                    
                    if hasattr(users_response, 'data') and users_response.data:
                        users_data = {user['id']: user for user in users_response.data}
                
                # Formatear comentarios con datos de usuario
                for comment in comments_response.data:
                    if isinstance(comment, dict):
                        user_id = comment.get('user_id')
                        user_info = users_data.get(user_id, {})
                        
                        formatted_comment = {
                            'id': comment.get('id'),
                            'content': comment.get('content'),
                            'created_at': comment.get('created_at'),
                            'user': {
                                'id': user_id,
                                'name': user_info.get('username', 'Usuario desconocido'),
                                'image': user_info.get('avatar_url', '')
                            }
                        }
                        comments.append(formatted_comment)
            
            # Calcular metadatos de paginación
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                "data": comments,
                "total": total,
                "page": page,
                "limit": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
            
        except Exception as e:
            print(f"Error al obtener comentarios: {e}")
            import traceback
            traceback.print_exc()
            return {
                "data": [], 
                "total": 0, 
                "page": page, 
                "limit": page_size,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False
            }
    
    @staticmethod
    def get_comment_count(news_id):
        """Obtener el número de comentarios para una noticia"""
        try:
            response = SupabaseClient.client.table('news_comment').select(
                'count', count='exact'
            ).eq('news_id', news_id).execute()
            
            return response.count if hasattr(response, 'count') else 0
            
        except Exception as e:
            print(f"Error al obtener conteo de comentarios: {e}")
            return 0
    
    @staticmethod
    def delete_comment(comment_id, user_id):
        """Eliminar un comentario (solo el autor puede hacerlo)"""
        try:
            comment = SupabaseClient.client.table('news_comment').select('news_id') \
                .eq('id', comment_id) \
                .eq('user_id', user_id) \
                .execute()
            
            if not comment.data or len(comment.data) == 0:
                return {"error": "Comment not found or you don't have permission to delete it"}
            
            news_id = comment.data[0]['news_id']
            
            SupabaseClient.client.table('news_comment').delete() \
                .eq('id', comment_id) \
                .execute()
            
            count = NewsInteractionService.get_comment_count(news_id)
            
            return {
                "success": True,
                "comment_count": count,
                "news_id": news_id
            }
            
        except Exception as e:
            print(f"Error al eliminar comentario: {e}")
            return {"error": str(e)} 