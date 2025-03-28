from infrastructure.supabase_client import SupabaseClient
from notifications_data import NOTIFICATIONS_DATA

class NotificationService:
    @staticmethod
    def push_notification(payload):
        try:
            language = payload.get('language')
            message_code = payload.get('message_code')
            user_id = payload.get('user_id')
            
            # Insert notification into database
            notification_data = {
                "language": language,
                "message_code": message_code,
                "user_id": user_id
            }
            
            # Get notification data from notifications_data.py
            notification_data = NOTIFICATIONS_DATA[message_code][language]
            
            notification = {
                "body": notification_data['message'],
                "title": notification_data['title'],
                "user_id": user_id
            }
            
            SupabaseClient.insert_notification(notification)
            return {"status": 200, "message": "Notification sent successfully"}
        
        except Exception as e:
            return {"status": 500, "message": str(e)}
