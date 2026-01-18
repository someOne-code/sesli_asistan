from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import logging
import sys

# --- CONFIGURATION ---
class Settings(BaseSettings):
    GROQ_API_KEY: str = Field(..., description="API Key for Groq")
    GEMINI_API_KEY: str = Field(None, description="API Key for Google Gemini")
    AI_PROVIDER: str = Field("groq", description="Selected AI Provider: 'groq' or 'gemini'")
    DB_NAME: str = Field("hedef.db", description="SQLite Database Name")
    SES_MODELI: str = Field("tr-TR-EmelNeural", description="TTS Voice Model")
    LOG_LEVEL: str = Field("INFO", description="Logging Level")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# --- ŞİRKET KİMLİK BİLGİLERİ ---
# Bu bilgileri buradan değiştirerek tüm sistemi güncelleyebilirsiniz.
COMPANY_INFO = {
    "ad": "Chinook Music Store",
    "asistan_adi": "Kurumsal Temsilci",
    "slogan": "Dijital müziğin merkezi.",
    "misyon": "Müşterilerimize veritabanımızdaki ürünler, fiyatlar ve stok durumu hakkında bilgi vermek.",
    "vizyon": "Küresel ölçekte dijital platform lideri olmak.",
    "iletisim": {
        "telefon": "N/A",
        "email": "support@chinook.com",
        "adres": "Dijital Platform (Merkez: New York)"
    },
    "iade_politikasi": "Dijital ürünlerde iade yoktur.",
    "calisma_saatleri": "7/24 Dijital Destek"
}

# Initialize settings
try:
    settings = Settings()
except Exception as e:
    print(f"Configuration Error: {e}")
    sys.exit(1)

# --- LOGGING SETUP ---
def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("VoiceAssistant")

logger = setup_logging()
