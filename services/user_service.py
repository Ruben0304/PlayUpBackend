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
