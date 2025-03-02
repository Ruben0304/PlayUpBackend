from infrastructure.supabase_client import SupabaseClient
from translations import COUNTRY_TRANSLATIONS

class CountryService:
    @staticmethod
    def get_countries(language: str = "en"):
        response = SupabaseClient.get_countries()
        data = response.data  # Lista de dicts

        for country in data:
            code = country.get("code")
            if code in COUNTRY_TRANSLATIONS:
                translations = COUNTRY_TRANSLATIONS[code]
                if language in translations:
                    country["name"] = translations[language]

        return {"countries": data}
