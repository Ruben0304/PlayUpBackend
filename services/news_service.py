from domain.models import NewsModel
from infrastructure.supabase_client import SupabaseClient
from translations import COUNTRY_TRANSLATIONS

class NewsService:
    @staticmethod
    def fetch(page=1, page_size=2):
        try:
            # Calcular el rango para la paginación
            start = (page - 1) * page_size
            end = start + page_size - 1
            
            # Obtener el total de registros
            count_response = SupabaseClient.client.table('news').select('count', count='exact').execute()
            total = count_response.count if hasattr(count_response, 'count') else 0
            
            # Obtener los datos paginados
            response = SupabaseClient.client.table('news').select('*').range(start, end).execute()
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
                
                processed_data.append(processed_item)
            
        except Exception as e:
            print(f"Error general: {e}")
            return {"error": str(e), "data": [], "total": 0, "limit": page_size, "page": page}

        return {"data": processed_data, "total": total, "limit": page_size, "page": page}
