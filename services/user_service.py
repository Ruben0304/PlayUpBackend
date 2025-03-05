from infrastructure.supabase_client import SupabaseClient
from services.notification_service import NotificationService

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
