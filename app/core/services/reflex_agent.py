"""
ReflexAgent - Provides immediate conversational fillers to mask latency.
Part of the Human-Like Voice AI layer.
"""

import random
from typing import Optional


class ReflexAgent:
    """
    Provides immediate conversational fillers for DOMAIN queries
    to mask database and LLM latency.
    
    Design Principles:
    - Lazy Coupling: No dependencies on DB or AI services
    - Single Responsibility: Only generates fillers
    - Test-First: All behavior is test-driven
    """
    
    def __init__(self):
        # Professional Turkish filler phrases
        self.domain_fillers = [
            "Hemen bakıyorum...",
            "Bir saniye, kontrol ediyorum...",
            "Kayıtlarımızda arayalım...",
            "Hemen buluyorum...",
            "Kontrol ediyorum...",
            "Bir dakika, bakıyorum...",
        ]
    
    async def get_filler(self, intent: str) -> Optional[str]:
        """
        Returns a conversational filler based on intent.
        
        Args:
            intent: One of CONVERSATION, DOMAIN, META, OFF_TOPIC
            
        Returns:
            A filler phrase for DOMAIN, None for others
        """
        if intent == "DOMAIN":
            return random.choice(self.domain_fillers)
        
        # No filler for CONVERSATION, META, or OFF_TOPIC
        return None
