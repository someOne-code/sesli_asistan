# -*- coding: utf-8 -*-
"""
Knowledge Repository Interface - Clean Architecture Contract
=============================================================
This interface defines the contract for accessing company knowledge.

CRITICAL RULES:
1. Core depends on THIS interface, not SQLite/SQL
2. Infrastructure implements this interface
3. NO hasattr checks - explicit contract only
4. SaaS-ready: topic_key is domain-agnostic

This enables:
- Testing with mocks
- Swapping DB backends
- Multi-tenant isolation
"""

from abc import ABC, abstractmethod
from typing import Optional


class IKnowledgeRepository(ABC):
    """
    Interface for accessing company/domain knowledge.
    
    This is NOT a product catalog - it's for:
    - Company info (vizyon, adres, iletisim)
    - Domain knowledge (SSS, policies, hours)
    - Static content (about, team, history)
    
    Implementation examples:
    - SqlKnowledgeRepository (company_info table)
    - JsonKnowledgeRepository (static files)
    - ApiKnowledgeRepository (CMS integration)
    """
    
    @abstractmethod
    def get(self, tenant_id: str, topic_key: str, locale: str = "tr") -> Optional[str]:
        """
        Retrieve knowledge content by topic key.
        
        CRITICAL: tenant_id is MANDATORY for multi-tenant isolation.
        NO silent defaults. NO fallbacks.
        
        Args:
            tenant_id: Tenant identifier (REQUIRED, no default)
            topic_key: Canonical topic identifier (e.g., 'vizyon', 'adres', 'kvkk')
            locale: Language/region code (default: 'tr')
            
        Returns:
            Content string if found, None otherwise
            
        Example:
            >>> repo.get("chinook_music", "vizyon")
            "Vizyonumuz: Yapay zeka ile iş dünyasını dönüştürmek."
            
            >>> repo.get("hotel_istanbul", "vizyon")
            "Vizyonumuz: Türkiye'nin en iyi oteli olmak."
            
        Raises:
            ValueError: If tenant_id is empty/None
        """
        pass
    
    @abstractmethod
    def exists(self, tenant_id: str, topic_key: str) -> bool:
        """
        Check if a topic exists without fetching content.
        
        Args:
            tenant_id: Tenant identifier (REQUIRED)
        
        Args:
            topic_key: Canonical topic identifier
            
        Returns:
            True if topic exists, False otherwise
        """
        pass
