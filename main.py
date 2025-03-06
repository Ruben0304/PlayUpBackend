import os
import logging
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file

from fastapi import FastAPI
from api import api
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@app.on_event("startup")
async def startup_event():
    logger.info(f"SUPABASE_URL: {SUPABASE_URL}")
    logger.info(f"SUPABASE_KEY: {SUPABASE_KEY}")
app.include_router(api.router)
