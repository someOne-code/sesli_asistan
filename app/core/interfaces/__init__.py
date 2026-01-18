from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from .query_normalizer import QueryNormalizer

class IDatabaseRepository(ABC):
    """
    Abstraction layer for Universal Retrieval.
    Decouples Service from Database specifics.
    """
    @abstractmethod
    def search_products(self, query: str, limit: int = 5, tenant_id: Optional[str] = None) -> List[Any]:
        """
        UNIVERSAL RETRIEVAL METHOD.
        Searches entire database (BusinessOfferings) for a specific tenant.
        """
        pass
    
    @abstractmethod
    def list_all_products(self, limit: int = 10, tenant_id: Optional[str] = None) -> List[Any]:
        """
        Returns a sample of products for catalog queries.
        """
        pass
        
    @abstractmethod
    def get_catalog_summary(self, tenant_id: Optional[str] = None) -> List[str]:
        """
        Returns a high-level summary of what this tenant offers.
        """
        pass

    @abstractmethod
    def get_safe_schema_summary(self) -> str:
        """
        Returns summary for AI context.
        """
        pass

    @abstractmethod
    def log_call(self, customer_text: str, ai_response: str, sentiment: str, summary: str, intent: Optional[str] = None):
        """
        Logs call for analytics.
        """
        pass

class IAIService(ABC):
    """
    Abstract interface for AI Services.
    """
    @abstractmethod
    def determine_intent(self, user_text: str) -> str:
        pass

    @abstractmethod
    def analyze_sentiment(self, user_text: str) -> str:
        pass

    @abstractmethod
    async def classify_text(self, system_prompt: str, user_text: str) -> str:
        """
        Raw LLM call for classification logic (bypassing Persona/Melody prompts).
        """
        pass
        
    # set_db_schema REMOVED (Legacy)

    @abstractmethod
    def generate_response(self, user_text: str, context: Any = None, conversation_history: str = "", is_first_message: bool = False) -> str:
        pass

    @abstractmethod
    def generate_response_stream(self, user_text: str, context: Any = None, conversation_history: str = "") -> AsyncIterator[str]:
        pass

    @abstractmethod
    def generate_command(self, user_text: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_summary(self, conversation_text: str) -> str:
        """
        Summarizes the conversation for long-term memory.
        """
        pass

