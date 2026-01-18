import logging
import os
import sys
from typing import List

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        # Try to set UTF-8 encoding for Windows console
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        # If reconfigure fails, we'll remove emojis from logs
        pass

# Check if console supports UTF-8
def supports_utf8():
    """Check if the console supports UTF-8 encoding"""
    try:
        # Try to encode an emoji
        '✅'.encode(sys.stdout.encoding or 'utf-8')
        return True
    except (UnicodeEncodeError, AttributeError):
        return False

USE_EMOJIS = supports_utf8()

# Emoji mapping (with fallbacks for Windows)
class LogEmoji:
    """Emoji constants with Windows-safe fallbacks"""
    if USE_EMOJIS:
        ROCKET = "🚀"
        CHECK = "✅"
        WARNING = "⚠️"
        ERROR = "❌"
        INFO = "ℹ️"
        MIC = "🎤"
        WRITE = "📝"
        TARGET = "🎯"
        SMILE = "😊"
        SEARCH = "🔍"
        DATABASE = "💾"
        CHAT = "💬"
        MEMORY = "📚"
        PHONE = "📞"
        SPEAKER = "🔊"
        SOUND_OFF = "🔇"
        TRASH = "🗑️"
        MASK = "🎭"
    else:
        ROCKET = "[START]"
        CHECK = "[OK]"
        WARNING = "[WARN]"
        ERROR = "[ERROR]"
        INFO = "[INFO]"
        MIC = "[MIC]"
        WRITE = "[TEXT]"
        TARGET = "[INTENT]"
        SMILE = "[SENTIMENT]"
        SEARCH = "[QUERY]"
        DATABASE = "[DB]"
        CHAT = "[CHAT]"
        MEMORY = "[MEM]"
        PHONE = "[CALL]"
        SPEAKER = "[AUDIO]"
        SOUND_OFF = "[MUTE]"
        TRASH = "[DEL]"
        MASK = "[PERSONA]"

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Settings:
    """Application configuration settings"""
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Database Configuration
    DB_NAME: str = os.getenv("DB_NAME", "chinook.db")
    DB_URL: str = os.getenv("DB_URL", None)  # For PostgreSQL/MySQL support
    
    # Redis Configuration (for conversation memory)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # AI Model Configuration
    SQL_GENERATION_MODEL: str = "llama-3.1-8b-instant"
    RESPONSE_GENERATION_MODEL: str = "llama-3.1-8b-instant"
    INTENT_CLASSIFICATION_MODEL: str = "llama-3.1-8b-instant"
    SENTIMENT_ANALYSIS_MODEL: str = "llama-3.1-8b-instant"
    SUMMARY_GENERATION_MODEL: str = "llama-3.1-8b-instant"
    
    # Temperature Settings (0.0 = deterministic, 1.0 = creative)
    SQL_TEMPERATURE: float = 0.1  # Very deterministic for SQL
    INTENT_TEMPERATURE: float = 0.1  # Consistent intent detection
    SENTIMENT_TEMPERATURE: float = 0.1  # Consistent sentiment analysis
    RESPONSE_TEMPERATURE: float = 0.5  # Slightly creative for responses
    SUMMARY_TEMPERATURE: float = 0.3  # Balanced for summaries
    
    # Query Configuration
    DEFAULT_SQL_LIMIT: int = 5
    MAX_SQL_LIMIT: int = 20
    
    # Audio Configuration
    SES_MODELI: str = "tr-TR-AhmetNeural"  # Turkish TTS voice
    WHISPER_MODEL: str = "whisper-large-v3"
    WHISPER_LANGUAGE: str = "tr"  # Turkish
    
    # Input Filtering
    MIN_INPUT_LENGTH: int = 3
    NOISE_PHRASES: List[str] = ["Altyazı", "altyazı", "Yükleyen", "yükleyen", ".", ""]
    
    # Company Identity
    DEFAULT_COMPANY_NAME: str = "Profesyonel Müşteri Hizmetleri Asistanı"
    
    # Session Configuration
    DEFAULT_SESSION_ID: str = "global_demo"
    SESSION_TIMEOUT_MINUTES: int = 30
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    @classmethod
    def validate(cls):
        """Validate critical settings"""
        if not cls.GROQ_API_KEY:
            logger.warning(f"{LogEmoji.WARNING} GROQ_API_KEY not set! AI features will not work.")
        
        if not os.path.exists(cls.DB_NAME) and not cls.DB_URL:
            logger.warning(f"{LogEmoji.WARNING} Database file '{cls.DB_NAME}' not found!")
        
        logger.info(f"{LogEmoji.CHECK} Configuration validated")


# Initialize settings validation on import
settings = Settings()
settings.validate()