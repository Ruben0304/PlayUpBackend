from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()  # Carga las variables de entorno desde .env

class Settings(BaseModel):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    DO_SPACES_KEY: str = os.getenv("DO_SPACES_KEY")
    DO_SPACES_SECRET: str = os.getenv("DO_SPACES_SECRET")
    DO_SPACES_BUCKET: str = "playup"
    DO_SPACES_REGION: str = "nyc3"
    DO_SPACES_ENDPOINT: str = "https://nyc3.digitaloceanspaces.com"

settings = Settings()

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
DO_SPACES_KEY = settings.DO_SPACES_KEY
DO_SPACES_SECRET = settings.DO_SPACES_SECRET
DO_SPACES_BUCKET = settings.DO_SPACES_BUCKET
DO_SPACES_REGION = settings.DO_SPACES_REGION
DO_SPACES_ENDPOINT = settings.DO_SPACES_ENDPOINT
