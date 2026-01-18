# -*- coding: utf-8 -*-
"""
Knowledge Resolver Tests - Architectural Boundary Enforcement
==============================================================
These tests enforce clean separation of concerns.

CRITICAL ASSERTIONS:
1. IntentClassifier does NOT extract topics
2. KnowledgeResolver owns semantic routing
3. Providers are swappable (dependency injection)
4. No hardcoded business logic

If these tests pass with the old architecture, they are WRONG.
"""

import pytest
from app.core.services.knowledge_resolver import KnowledgeResolver, KnowledgeRequest
from app.core.interfaces.signal_providers import IScopeSignalProvider, ITopicSignalProvider


class MockScopeProvider(IScopeSignalProvider):
    """Mock provider for testing."""
    
    def get_company_signals(self):
        return {"vizyon", "vizyonunuz", "adres", "neredesiniz", "iletişim"}
    
    def get_product_signals(self):
        return {"fiyat", "stok", "ürün", "şarkı", "albüm"}


class MockTopicProvider(ITopicSignalProvider):
    """Mock provider for testing."""
    
    def resolve_topic(self, text: str) -> str:
        mapping = {
            "vizyon": "vizyon",
            "vizyonunuz": "vizyon",
            "adres": "adres",
            "neredesiniz": "adres",
            "iletişim": "iletisim"
        }
        for signal, topic in mapping.items():
            if signal in text:
                return topic
        return "genel"
    
    def get_topic_signals(self):
        return {
            "vizyon": "vizyon",
            "vizyonunuz": "vizyon",
            "adres": "adres",
            "neredesiniz": "adres"
        }


class TestKnowledgeResolver:
    """
    Test suite for KnowledgeResolver.
    
    These tests enforce:
    - Scope detection is provider-driven
    - Topic extraction is provider-driven
    - No hardcoded business logic
    """
    
    def test_company_scope_resolution(self):
        """
        CRITICAL: Company queries resolve to knowledge repository.
        """
        resolver = KnowledgeResolver(
            scope_provider=MockScopeProvider(),
            topic_provider=MockTopicProvider()
        )
        
        request = resolver.resolve("vizyonunuz nedir", {})
        
        assert request.scope == "company"
        assert request.target == "knowledge"
        assert request.topic_key == "vizyon"
    
    def test_product_scope_resolution(self):
        """
        CRITICAL: Product queries resolve to catalog repository.
        """
        resolver = KnowledgeResolver(
            scope_provider=MockScopeProvider(),
            topic_provider=MockTopicProvider()
        )
        
        request = resolver.resolve("fiyatlar nedir", {})
        
        assert request.scope == "product"
        assert request.target == "catalog"
    
    def test_topic_extraction_uses_provider(self):
        """
        CRITICAL: Topic extraction delegated to provider, not hardcoded.
        """
        resolver = KnowledgeResolver(
            scope_provider=MockScopeProvider(),
            topic_provider=MockTopicProvider()
        )
        
        request = resolver.resolve("neredesiniz", {})
        
        # Topic should be resolved via provider
        assert request.topic_key == "adres"
    
    def test_provider_swappability(self):
        """
        CRITICAL: Different providers = different behavior (SaaS ready).
        """
        class HotelScopeProvider(IScopeSignalProvider):
            def get_company_signals(self):
                return {"rezervasyon", "konum", "hizmetler"}
            
            def get_product_signals(self):
                return {"oda", "fiyat", "müsaitlik"}
        
        class HotelTopicProvider(ITopicSignalProvider):
            def resolve_topic(self, text: str) -> str:
                if "rezervasyon" in text:
                    return "booking"
                return "general"
            
            def get_topic_signals(self):
                return {"rezervasyon": "booking"}
        
        resolver = KnowledgeResolver(
            scope_provider=HotelScopeProvider(),
            topic_provider=HotelTopicProvider()
        )
        
        request = resolver.resolve("rezervasyon yapmak istiyorum", {})
        
        # Should use hotel-specific logic
        assert request.scope == "company"
        assert request.topic_key == "booking"


class TestArchitecturalBoundaries:
    """
    Tests that enforce architectural separation.
    
    These MUST fail if:
    - IntentClassifier extracts topics
    - AssistantService has business logic
    - Hardcoded assumptions leak
    """
    
    def test_intent_classifier_does_not_extract_topics(self):
        """
        CRITICAL: IntentClassifier only classifies, does NOT extract topics.
        
        This test will FAIL until we refactor IntentExtractor.
        """
        from app.core.services.intent_extractor import IntentExtractor
        
        extractor = IntentExtractor()
        result = extractor.classify("vizyonunuz nedir")
        
        # IntentClassifier should NOT have topic in meta_data
        # It should only have minimal hints
        assert result.intent.value == "INFORMATIONAL"
        
        # CRITICAL: Topic extraction should NOT be in IntentClassifier
        # This assertion will FAIL with current implementation
        assert "topic" not in result.meta_data, \
            "IntentClassifier MUST NOT extract topics - that's KnowledgeResolver's job!"
    
    def test_knowledge_request_structure(self):
        """
        Verify KnowledgeRequest has correct structure.
        """
        request = KnowledgeRequest(
            scope="company",
            target="knowledge",
            topic_key="vizyon",
            confidence=1.0
        )
        
        assert request.scope == "company"
        assert request.target == "knowledge"
        assert request.topic_key == "vizyon"
        assert 0.0 <= request.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
