from fastapi import Request
from infrastructure.supabase_client import SupabaseClient
from services.user_service import UserService
# from gotrue import SignInWithPasswordCredentials

class AuthService:
    @staticmethod
    async def refresh_token(payload):
        response = SupabaseClient.client.auth.refresh_session(payload['refresh_token'])
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }
