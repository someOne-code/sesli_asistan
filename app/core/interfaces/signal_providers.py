# -*- coding: utf-8 -*-
"""
Signal Provider Interfaces - Lazy Coupling Pattern
===================================================
These interfaces enable data-driven behavior without hardcoding.

CRITICAL: Classifiers MUST NOT hardcode business logic.
Instead, they query providers for signals/hints.

This enables:
- Multi-tenant: Different customers, different signals
- Multi-domain: Music store vs Hotel vs Restaurant
- Admin control: Signals managed via UI/DB
- Testing: Mock providers for unit tests
"""

from abc import ABC, abstractmethod
from typing import Set, Dict


class IScopeSignalProvider(ABC):
    """
    Provides signals that indicate query scope.
    
    Scope examples:
    - company: Questions about the business itself
    - product: Questions about catalog items
    - general: Generic information requests
    
    SaaS Pattern:
    - Music Store: company signals = ["vizyon", "adres"]
    - Hotel: company signals = ["rezervasyon", "konum", "hizmetler"]
    - Restaurant: company signals = ["menü", "adres", "açılış saatleri"]
    """
    
    @abstractmethod
    def get_company_signals(self) -> Set[str]:
        """
        Get signals that indicate company-scope queries.
        
        Returns:
            Set of lowercase keywords/phrases
            
        Example:
            {"vizyon", "misyon", "adres", "iletişim", "hakkında"}
        """
        pass
    
    @abstractmethod
    def get_product_signals(self) -> Set[str]:
        """
        Get signals that indicate product-scope queries.
        
        Returns:
            Set of lowercase keywords/phrases
            
        Example:
            {"fiyat", "stok", "satın", "ürün", "şarkı", "albüm"}
        """
        pass


class ITopicSignalProvider(ABC):
    """
    Maps user signals to canonical topic keys.
    
    This is the "dictionary" that translates:
    - User language -> Database keys
    - Synonyms -> Single canonical form
    - Multi-language -> Unified topics
    
    SaaS Pattern:
    - Same topic_key across all tenants
    - Different signals per tenant/language
    - Centrally managed via DB/config
    """
    
    @abstractmethod
    def resolve_topic(self, text: str) -> str:
        """
        Extract canonical topic key from user text.
        
        Args:
            text: Normalized user input
            
        Returns:
            Canonical topic_key for knowledge lookup
            
        Example:
            >>> provider.resolve_topic("vizyonunuz nedir")
            "vizyon"
            
            >>> provider.resolve_topic("neredesiniz")
            "adres"
            
            >>> provider.resolve_topic("random text")
            "genel"  # Default fallback
        """
        pass
    
    @abstractmethod
    def get_topic_signals(self) -> Dict[str, str]:
        """
        Get full mapping of signals to topic keys.
        
        Returns:
            Dict mapping user signals to canonical keys
            
        Example:
            {
                "vizyon": "vizyon",
                "vizyonunuz": "vizyon",
                "misyon": "misyon",
                "adres": "adres",
                "neredesiniz": "adres"
            }
        """
        pass
