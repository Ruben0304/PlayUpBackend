from infrastructure.supabase_client import SupabaseClient
from services.notification_service import NotificationService
from fastapi import Request, HTTPException

class UserService:
    @staticmethod
    def updateToOrganizerRole(user_id: str):
        response = SupabaseClient.update_user_role(user_id, "organizer")
        return response.data is not None

    @staticmethod
    def approve_organizer_from_waitlist(user_id: str) -> None:
        try:
            # Get organizer role id
            organizer_role = SupabaseClient.get_role_by_name('organizer')
            organizer_role_id = organizer_role.data['id']
            
            supabase = SupabaseClient()

            # Update user role in user_role table
            supabase.client.table('user_role').update({'role': organizer_role_id}).eq('user', user_id).execute()
            
            # Update approved status in organizer_waitlist table
            supabase.client.table('organizer_waitlist').update({'approved': True}).eq('user', user_id).execute()
            
            notification = {
                'user_id': user_id,
                'message_code': "organizer_role_approved",
                'language': "es"
            }
            
            NotificationService.push_notification(notification)
            
            return True
        except Exception as e:
            print(f"Error approving organizer: {str(e)}")
            raise e

    @staticmethod
    async def get_user_from_token(request: Request, required=False):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            if required:
                raise HTTPException(status_code=401, detail="Authorization header is required")
            return None
        
        try:
            # Extraer el token
            token = auth_header.split(' ')[1]
            # Obtener el usuario usando el token
            user = SupabaseClient.client.auth.get_user(token)
            if not user or not hasattr(user.user, 'id'):
                if required:
                    raise HTTPException(status_code=401, detail="Invalid token or user not found")
                return None
            
            return user.user.id
        except Exception as e:
            if required:
                raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")
            print(f"Error al obtener usuario del token: {e}")
            return None

    @staticmethod
    def is_admin(user_id):
        try:
            # Verificar si el usuario tiene rol de administrador
            response = SupabaseClient.client.table('user_role').select('role').eq('user', user_id).execute()
            
            if not response.data:
                return False
            
            # Obtener el ID del rol de administrador
            admin_role = SupabaseClient.get_role_by_name('admin')
            if not admin_role.data:
                return False
            
            admin_role_id = admin_role.data['id']
            
            # Verificar si el usuario tiene el rol de administrador
            for role in response.data:
                if role.get('role') == admin_role_id:
                    return True
            
            return False
        except Exception as e:
            print(f"Error al verificar si el usuario es administrador: {e}")
            return False
            
    @staticmethod
    def get_user_profiles(user_id):
        """
        Obtiene todos los perfiles con los que un usuario puede publicar:
        - Su perfil de usuario
        - Equipos que posee
        - Organizaciones a las que pertenece
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de perfiles con id, name e image
        """
        try:
            profiles = []
            
            # 1. Perfil de usuario (siempre disponible)
            user_response = SupabaseClient.client.table('user').select('id,username,avatar_url').eq('id', user_id).single().execute()
            if user_response.data:
                user_type_response = SupabaseClient.client.table('user_type').select('id').eq('name', 'user').single().execute()
                user_type_id = user_type_response.data.get('id') if user_type_response.data else None
                
                profiles.append({
                    'id': str(user_response.data['id']),
                    'name': user_response.data.get('username', ''),
                    'image': user_response.data.get('avatar_url', '')
                })
            
            # 2. Equipos que posee el usuario
            team_response = SupabaseClient.client.table('team').select('id,name,logo').eq('user', user_id).execute()
            if team_response.data:
                team_type_response = SupabaseClient.client.table('user_type').select('id').eq('name', 'team').single().execute()
                team_type_id = team_type_response.data.get('id') if team_type_response.data else None
                
                for team in team_response.data:
                    profiles.append({
                        'id': str(team['id']),
                        'name': team.get('name', ''),
                        'image': team.get('logo', '')
                    })
            
            # 3. Organizaciones a las que pertenece (como admin o miembro con permisos)
            try:
                # Obtener las organizaciones a las que pertenece el usuario
                org_member_response = SupabaseClient.client.table('user_organization').select('organization').eq('user', user_id).execute()
                
                if org_member_response.data:
                    org_ids = [member['organization'] for member in org_member_response.data]
                    
                    # Obtener detalles de las organizaciones
                    for org_id in org_ids:
                        org_response = SupabaseClient.client.table('organization').select('id,name,logo').eq('id', org_id).single().execute()
                        if org_response.data:
                            profiles.append({
                                'id': str(org_response.data['id']),
                                'name': org_response.data.get('name', ''),
                                'image': org_response.data.get('logo', '')
                            })
            except Exception as org_error:
                # Si la tabla no existe o hay otro error, simplemente continuamos
                print(f"Error al obtener organizaciones: {org_error}")
            
            # Nota: Se omite la sección de torneos porque la tabla tournament_admin no existe en el esquema actual.
            # Si se necesita obtener torneos asociados al usuario, se debe implementar otra lógica basada en las tablas existentes.
            
            return profiles
            
        except Exception as e:
            print(f"Error al obtener perfiles del usuario: {e}")
            import traceback
            traceback.print_exc()
            return []
