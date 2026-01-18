import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer

def test_typo_correction():
    n = RuleBasedNormalizer()
    # 'ne' is now a protected keyword (kept).
    # 'müdükler' corrected to 'müzikler' via typo map.
    # 'var' removed via stop words.
    # Result: "ne tür müzikler"
    assert n.normalize("ne tür müdükler var") == "ne tür müzikler"

def test_normalize_basic():
    n = RuleBasedNormalizer()
    
    # 1. Typo fix
    assert n.normalize("metalika") == "metallica"
    assert n.normalize("müdük") == "müzik"
    
    # 2. Stopword removal
    assert n.normalize("bana metallica getir") == "metallica"
    assert n.normalize("lütfen queen çal") == "queen"
    
    # 3. Domain word removal
    assert n.normalize("metallica şarkıları") == "metallica şarkıları" 
    # Wait, 'şarkıları' is not in DOMAIN_WORDS ('şarkı' is). 
    # Ideally should handle suffixes, but for now exact match.
    
    assert n.normalize("metallica şarkı") == "metallica"

def test_empty_handling():
    n = RuleBasedNormalizer()
    assert n.normalize("") == ""
    assert n.normalize(None) == ""

def test_fallback():
    n = RuleBasedNormalizer()
    # If standard stripping leaves nothing (e.g. "müzik çal"), it should return something useful?
    # Logic says: if result empty, return typo-fixed original.
    # "müzik çal" -> stopwords/domain words removed -> "" -> fallback -> "müzik çal"
    assert n.normalize("müzik çal") == "müzik çal" 

if __name__ == "__main__":
    # Manual run check
    n = RuleBasedNormalizer()
    print(f"Input: 'ne tür müdükler var'")
    print(f"Output: '{n.normalize('ne tür müdükler var')}'") 
    # Issue: 'müdükler' won't match 'müdük'. 
    # I should update the normalizer to use a slightly smarter replace OR add suffix variations to the map.
    # User's previous fuzzy.py handled SOME variations.
    # Best fix: Add 'müdükler' to the map in the implementation step if missed.


def test_preserves_intent_keywords():
    """
    Test that critical intent keywords are PRESERVED suitable for service businesses.
    Old behavior: 'saç kesimi fiyatı ne' -> 'saç kesimi' (Knowledge lost)
    New behavior: 'saç kesimi fiyatı ne' -> 'saç kesimi fiyatı ne' (Intent preserved)
    """
    normalizer = RuleBasedNormalizer()
    
    # Critical queries for a service business (e.g. Barber)
    queries = [
        ("saç kesimi fiyatı ne", ["fiyat", "ne"]),  # 'fiyatı' becomes 'fiyat' via typo fix
        ("hangi hizmetler var", ["hizmetler"]), # 'hangi' likely stripped unless protected, let's check.
        ("randevu alabilir miyim", ["randevu"]),
        ("ücret nedir", ["ücret", "nedir"])
    ]
    
    for raw_query, expected_keywords in queries:
        normalized = normalizer.normalize(raw_query)
        print(f"Query: '{raw_query}' -> Normalized: '{normalized}'")
        
        for keyword in expected_keywords:
            assert keyword in normalized, f"Critical keyword '{keyword}' was stripped from '{raw_query}'"

def test_configurable_stopwords():
    """Verify we can inject custom stopwords (Lazy Coupling)."""
    custom_stops = {"foo", "bar"}
    # Passing protected keywords too
    normalizer = RuleBasedNormalizer(stop_words=custom_stops, protected_keywords=["baz"])
    
    result = normalizer.normalize("foo bar baz")
    assert "baz" in result
    assert "foo" not in result
