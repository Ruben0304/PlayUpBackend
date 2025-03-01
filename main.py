from fastapi import FastAPI, Query
from supabase import create_client, Client

from translations import COUNTRY_TRANSLATIONS

# Credenciales Supabase
SUPABASE_URL = "https://tnuvhxvelwizhieiiglq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRudXZoeHZlbHdpemhpZWlpZ2xxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY4OTgzMzI3NywiZXhwIjoyMDA1NDA5Mjc3fQ.D1sc8Qug8ua2nO0xf3_xJkp5Bx7bBP3ZS_snAwehODg"

app = FastAPI()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Diccionario local de traducciones (ejemplo simplificado)


@app.get("/countries")
async def get_countries(language: str = "en"):
    # 1. Obtener los países de Supabase
    response = supabase.table("country").select("*").execute()
    data = response.data  # Lista de dicts

    # 2. Reemplazar el nombre por la traducción
    for country in data:
        code = country.get("code")
        if code in COUNTRY_TRANSLATIONS:
            translations = COUNTRY_TRANSLATIONS[code]
            # Si el idioma existe en el diccionario, lo usamos
            if language in translations:
                country["name"] = translations[language]

    return {"countries": data}
