"""
Lightweight Semantic Human Intent Classifier
Runs before any database or domain logic to understand user's true intent.
"""

from typing import Literal
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

IntentType = Literal["CONVERSATION", "DOMAIN", "META", "OFF_TOPIC"]


class IntentClassifier:
    """
    Classifies user utterances into one of four categories:
    - CONVERSATION: greetings, small talk, social interaction
    - DOMAIN: product/music queries, prices, catalog
    - META: system checks (can you hear me, are you there)
    - OFF_TOPIC: irrelevant, personal, forbidden topics
    """
    
    def __init__(self, ai_service):
        """
        Args:
            ai_service: An instance of IAIService (GroqAIService or similar)
        """
        self.ai = ai_service
        
    async def classify(self, text: str) -> IntentType:
        """
        Classify user intent using a minimal LLM call.
        
        Args:
            text: User's raw input
            
        Returns:
            One of: CONVERSATION, DOMAIN, META, OFF_TOPIC
        """
        if not text or not text.strip():
            return "OFF_TOPIC"
            
        # System prompt for classification
        system_prompt = """You are classifying a phone call sentence for a company call-center.

Decide the user's INTENT, not the topic.

Return ONLY one word:

CONVERSATION → greeting, small talk, social interaction
DOMAIN → asking about products, music, prices, catalog
META → system check (can you hear me, are you there)
OFF_TOPIC → irrelevant, personal, forbidden topics

Examples:
"Naber moruk" → CONVERSATION
"Hi, are you there?" → META
"What's your favorite color?" → OFF_TOPIC
"Saç kesimi fiyatı" → DOMAIN
"Sesim geliyor mu?" → META
"Merhaba" → CONVERSATION
"Hangi hizmetler var?" → DOMAIN
"Yemek siparişi verebilir miyim?" → OFF_TOPIC

Return ONLY the classification word, nothing else."""

        user_prompt = f'Sentence:\n"{text}"'
        
        try:
            # Make a minimal LLM call
            response = await self.ai.classify_text(
                system_prompt=system_prompt,
                user_text=user_prompt
            )
            
            # Extract the classification
            classification = response.strip().upper()
            
            # Validate and return
            valid_intents = ["CONVERSATION", "DOMAIN", "META", "OFF_TOPIC"]
            if classification in valid_intents:
                return classification
            
            # Fallback: if response contains the word, extract it
            for intent in valid_intents:
                if intent in classification:
                    return intent
                    
            # Default fallback
            logger.warning(f"[INTENT_CLASSIFIER] Unexpected response: {response}, defaulting to DOMAIN")
            return "DOMAIN"
            
        except Exception as e:
            logger.error(f"[INTENT_CLASSIFIER] Error: {e}, defaulting to DOMAIN")
            return "DOMAIN"

    async def get_refined_intent(self, text: str) -> str:
        """
        SMART PATH: Uses LLM to understand complex intents when Regex fails.
        Returns mapped Intent aliases: LIST_CATALOG, SEARCH_PRODUCT, INFORMATIONAL, SOCIAL.
        """
        system_prompt = """
        Analyze the user's intent for a business voice assistant.
        
        Classify into exactly one of these CATEGORIES:
        - LIST_CATALOG: User wants to see what is available (menu, services, products).
          (e.g., "Neler yapıyorsunuz?", "Hizmetleriniz neler?", "Menüde ne var?", "Katalog")
        - SEARCH_PRODUCT: User asks for specific item or price.
          (e.g., "Saç kesimi ne kadar?", "Metallica var mı?", "Ucuz bir şey öner")
        - INFORMATIONAL: User asks about company identity, location, hours.
          (e.g., "Vizyonunuz ne?", "Neredesiniz?", "Kaçta açılıyorsunuz?", "Randevu alabilir miyim?")
        - SOCIAL: Small talk, greetings, off-topic.
          (e.g., "Selam", "Nasılsın", "Hava durumu")
          
        INPUT: User sentence.
        OUTPUT: Return ONLY the Category Name.
        """
        
        try:
            category = await self.ai.classify_text(system_prompt, text)
            category = category.strip().upper()
            
            # Validation
            valid = {"LIST_CATALOG", "SEARCH_PRODUCT", "INFORMATIONAL", "SOCIAL"}
            # Clean up common LLM noise
            for v in valid:
                if v in category:
                    return v
                    
            return "SEARCH_PRODUCT" # Default fallback
            
        except Exception as e:
            logger.error(f"[SMART_INTENT] Error: {e}")
            return "SEARCH_PRODUCT"
