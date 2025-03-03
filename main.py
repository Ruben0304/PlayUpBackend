import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file

from fastapi import FastAPI
from api import api

app = FastAPI()

app.include_router(api.router)
