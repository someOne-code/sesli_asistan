"""
Test suite for Deterministic Intent Extraction.
This is the SPECIFICATION - tests define the expected behavior.
DO NOT MODIFY TESTS TO FIT CODE. Code must pass these tests.
"""

import pytest
from app.core.services.intent_extractor import IntentExtractor, IntentType, IntentResult

@pytest.fixture
def extractor():
    return IntentExtractor()

# =========================================================================
# SIMPLE SEARCH TESTS
# =========================================================================

def test_simple_search(extractor):
    """
    Input: "Metallica çal"
    Expect: intent=SEARCH_PRODUCT, query="metallica", filters={}
    """
    result = extractor.classify("Metallica çal")
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert result.query_term == "metallica"
    assert result.filters == {}

def test_reverse_phrasing(extractor):
    """
    Input: "Çal Tarkan"
    Expect: intent=SEARCH_PRODUCT, query="tarkan"
    """
    result = extractor.classify("Çal Tarkan")
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert result.query_term == "tarkan"

# =========================================================================
# FILTERED SEARCH TESTS
# =========================================================================

def test_filtered_search_cheap(extractor):
    """
    Input: "En ucuz Iron Maiden"
    Expect: intent=SEARCH_PRODUCT, query="iron maiden", filters={'sort': 'price_asc'}
    """
    result = extractor.classify("En ucuz Iron Maiden")
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert result.query_term == "iron maiden"
    assert result.filters == {'sort': 'price_asc'}

def test_filtered_search_expensive(extractor):
    """
    Input: "En pahalı rock albümü"
    Expect: intent=SEARCH_PRODUCT, query="rock albümü", filters={'sort': 'price_desc'}
    """
    result = extractor.classify("En pahalı rock albümü")
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert "rock" in result.query_term
    assert result.filters == {'sort': 'price_desc'}

# =========================================================================
# CATALOG QUERY TESTS
# =========================================================================

def test_catalog_query(extractor):
    """
    Input: "Ne tür müzikler var?"
    Expect: intent=LIST_CATALOG, query=None
    """
    result = extractor.classify("Ne tür müzikler var?")
    assert result.intent == IntentType.LIST_CATALOG
    assert result.query_term is None

def test_catalog_query_variant(extractor):
    """
    Input: "Hangi kategoriler mevcut"
    Expect: intent=LIST_CATALOG
    """
    result = extractor.classify("Hangi kategoriler mevcut")
    assert result.intent == IntentType.LIST_CATALOG

# =========================================================================
# SEMANTIC GATING / STOP WORD TESTS
# =========================================================================

def test_empty_after_stopword_removal(extractor):
    """
    Input: "çal" (No term left after stop word removal)
    Expect: intent=SOCIAL (was UNKNOWN, now casual_chat)
    """
    result = extractor.classify("çal")
    assert result.intent == IntentType.SOCIAL
    assert result.meta_data["subtype"] == "casual_chat"

def test_complex_sentence(extractor):
    """
    Input: "Bana en ucuz Metallica şarkısını çal"
    Expect: intent=SEARCH_PRODUCT, query contains "metallica", filters={'sort': 'price_asc'}
    """
    result = extractor.classify("Bana en ucuz Metallica şarkısını çal")
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert "metallica" in result.query_term
    assert result.filters == {'sort': 'price_asc'}

# =========================================================================
# SEMANTIC GROUPING & SUBTYPE TESTS (New Requirements)
# =========================================================================

def test_context_reference_subtype(extractor):
    """
    Test: "bu nedir" → SOCIAL with context_ref subtype
    Regression: Previously searched for product named "bu"
    """
    result = extractor.classify("bu nedir")
    
    assert result.intent == IntentType.SOCIAL
    assert result.query_term is None
    assert result.meta_data["subtype"] == "context_ref"

def test_clarification_subtype(extractor):
    """
    Test: "ürünleriniz" → SOCIAL with clarification subtype
    Regression: Previously returned UNKNOWN intent
    """
    result = extractor.classify("ürünleriniz")
    
    assert result.intent == IntentType.SOCIAL
    assert result.query_term is None
    assert result.meta_data["subtype"] == "clarification"

def test_katalog_is_clarification(extractor):
    """
    Test: "katalog" -> SOCIAL with clarification subtype
    Note: "katalog" without specific intent triggers clarification about WHAT catalog items they want
    """
    result = extractor.classify("katalog")
    
    assert result.intent == IntentType.SOCIAL
    assert result.meta_data["subtype"] == "clarification"

def test_wildcard_search_with_filter(extractor):
    """
    Test: "en pahalı ürün" -> SEARCH_PRODUCT with query=None
    """
    result = extractor.classify("en pahalı ürün")
    
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert result.query_term is None
    assert result.filters == {"sort": "price_desc"}

def test_pronoun_priority_over_clarification(extractor):
    """
    Test: "bu ürün nedir" -> context_ref (not clarification)
    Priority: context_ref > clarification
    """
    result = extractor.classify("bu ürün nedir")
    
    assert result.intent == IntentType.SOCIAL
    assert result.meta_data["subtype"] == "context_ref"  # Priority 1

def test_metallica_regression(extractor):
    """
    Test: "Metallica çal" -> SEARCH_PRODUCT with query="metallica"
    Regression: Ensure normal search still works after semantic changes
    """
    result = extractor.classify("Metallica çal")
    
    assert result.intent == IntentType.SEARCH_PRODUCT
    assert result.query_term == "metallica"

def test_promoted_fillers_as_wildcard(extractor):
    """
    Test: "bana en güzel ürününü göster"
    Expect: 'güzel' is a stop word, 'ürün' is a clarification word (stop word).
    Result should be SOCIAL (clarification) OR UNKNOWN if no filters.
    Unless 'güzel' is ignored and we fall through.
    """
    # "bana" (stop), "en" (stop), "güzel" (stop), "ürününü" (stop), "göster" (stop)
    # Result: Empty query. No filters. -> SOCIAL query
    result = extractor.classify("bana en güzel ürününü göster")
    
    assert result.intent == IntentType.SOCIAL
    # subtype priority: 'ürününü' -> clarification
    assert result.meta_data["subtype"] == "clarification"
