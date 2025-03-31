import os

import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # Load environment variables from a .env file

from fastapi import FastAPI
from api import api

app = FastAPI()



# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app.include_router(api.router)


# Punto de entrada para ejecutar la aplicación
if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # Módulo y nombre de la aplicación
        host="127.0.0.1",  # Escucha en todas las interfaces
        port=8000,  # Puerto por defecto
        reload=True,  # Recarga automática en desarrollo
        log_level="info"  # Nivel de logs
    )

