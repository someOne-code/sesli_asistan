# -*- coding: utf-8 -*-
"""
Default Signal Providers - Production-Ready Implementations
============================================================
These are the default implementations of signal provider interfaces.

DEPLOYMENT STRATEGY:
- Sprint 1: Use these hardcoded defaults
- Sprint 2: Load from database/config
- Sprint 3: Admin UI for signal management

SaaS Pattern:
- Each tenant can override these providers
- Signals stored in tenant-specific tables
- Multi-language support via locale-specific providers
"""

from typing import Set, Dict
from app.core.interfaces.signal_providers import IScopeSignalProvider, ITopicSignalProvider


class DefaultScopeProvider(IScopeSignalProvider):
    """
    Default scope signal provider for music store domain.
    
    This implementation is music-store-specific.
    For other domains (hotel, restaurant), create domain-specific providers.
    """
    
    def get_company_signals(self) -> Set[str]:
        """
        Company-scope signals for music store.
        
        These indicate user is asking about the BUSINESS, not products.
        """
        return {
            # Identity
            "vizyon", "vizyonunuz", "misyon", "misyonunuz",
            "kimsiniz", "kimsin", "nesiniz", "hakkında", "hakkınızda",
            # Location
            "adres", "adresiniz", "neredesiniz", "nerede", "konum", "lokasyon",
            # Contact
            "iletişim", "telefon", "mail", "email", "ulaşım", "ulaşabilirim",
            # Company
            "şirket", "firma", "kuruluş"
        }
    
    def get_product_signals(self) -> Set[str]:
        """
        Product-scope signals for music store.
        
        These indicate user is asking about CATALOG items.
        """
        return {
            "fiyat", "kaç", "stok", "var mı", "ne kadar", "ücret",
            "satın", "sipariş", "al", "ürün", "şarkı", "albüm", "müzik"
        }


class DefaultTopicProvider(ITopicSignalProvider):
    """
    Default topic signal provider for music store domain.
    
    Maps user signals to canonical topic keys for database lookup.
    """
    
    def __init__(self):
        """Initialize topic mapping."""
        self._topic_mapping = {
            # Identity
            "vizyon": "vizyon",
            "vizyonunuz": "vizyon",
            "misyon": "misyon",
            "misyonunuz": "misyon",
            "kimsiniz": "hakkinda",
            "kimsin": "hakkinda",
            "hakkında": "hakkinda",
            "hakkınızda": "hakkinda",
            # Location
            "adres": "adres",
            "adresiniz": "adres",
            "neredesiniz": "adres",
            "nerede": "adres",
            "konum": "adres",
            "lokasyon": "adres",
            # Contact
            "iletişim": "iletisim",
            "telefon": "iletisim",
            "mail": "iletisim",
            "email": "iletisim",
            "ulaşım": "iletisim",
            "ulaşabilirim": "iletisim",
            # Company
            "şirket": "hakkinda",
            "firma": "hakkinda",
            "kuruluş": "hakkinda"
        }
    
    def resolve_topic(self, text: str) -> str:
        """
        Extract canonical topic key from user text.
        
        Args:
            text: Normalized user input (lowercase)
            
        Returns:
            Canonical topic_key for knowledge lookup
        """
        # Find first matching signal
        for signal, topic_key in self._topic_mapping.items():
            if signal in text:
                return topic_key
        
        # Default fallback
        return "genel"
    
    def get_topic_signals(self) -> Dict[str, str]:
        """
        Get full mapping of signals to topic keys.
        
        Returns:
            Dict mapping user signals to canonical keys
        """
        return self._topic_mapping.copy()
