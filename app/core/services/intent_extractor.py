"""
Deterministic Intent Extractor.
PURE DOMAIN LOGIC - No LLM, No Database, No External APIs.
Converts raw user text into structured, machine-readable command objects.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Set, Dict, Any
import re


# ============================================================================
# SEMANTIC WORD GROUPS (Single Source of Truth - DRY Compliance)
# ============================================================================
# These groups serve dual purposes:
# 1. Stop words: Removed from search queries to prevent false positives
# 2. Subtype triggers: Used to determine SOCIAL intent granularity
# ============================================================================

# 1. CONTEXT REFERENCE WORDS
# Pronouns referring to previous conversation items
# Examples: "Bu nedir?" (What is THIS?), "Şu kaç para?" (How much is THAT?)
CONTEXT_REF_WORDS = frozenset({
    "bu", "şu", "o",           # Singular pronouns
    "bunlar", "şunlar", "onlar" # Plural pronouns
})

# 2. CLARIFICATION WORDS
# Generic domain terms requiring user clarification
# Examples: "Ürünleriniz nedir?" (What are your products?), "Katalog" (Catalog)
CLARIFICATION_WORDS = frozenset({
    "ürün", "ürünler", "ürününüz", "ürünleriniz", "ürününü", "ürünlerini",  # Product variants
    "katalog", "kategoriler", "tür", "tarz",       # Catalog variants
    "şey", "şeyler", "var", "yok",                 # Generic things
    "satıyorsunuz", "satış", "satılık", "ne satıyorsunuz", "ne satılıyor" # Selling related
})

# 3. QUESTION WORDS
# Interrogatives that don't contribute to search terms
# Examples: "Nedir bu?" (What is this?), "Hangi şarkı?" (Which song?)
QUESTION_WORDS = frozenset({
    "nedir", "ne", "neler",     # What variations
    "hangi", "hangisi",         # Which variations
    "nasıl",                    # How
    "bana", "göster", "söyle", "anlat", "bul", "getir", # Commands
    "misin", "mısın", "musun", "müsün", "mi", "mı", "mu", "mü" # Question particles
})

# 4. GENERIC QUANTIFIERS & FILLERS
# Modal verbs and quantifiers that create false positives if searched
GENERIC_WORDS = frozenset({
    "tane", "adet",  # Pieces, units
    "en", "bir", "daha", "çok", "kadar", # Quantifiers
    "olan", "olarak", "ve", "ile", "için", "de", "da", # Conjunctions
    "güzel", "iyi", "kötü", "harika", "popüler", "pahalı", "ucuz", # Subjective/Adjectives
    "merhaba", "selam", "günaydın", "iyi", "akşamlar", "günler", "geceler" # Greetings
})

# 5. COMMAND VERBS (Explicit Actions)
# Verbs that indicate action but shouldn't be part of the search query
COMMAND_WORDS = frozenset({
    "çal", "oynat", "dinle", "aç", "açar",      # Play commands
    "bul", "getir", "göster", "listele",        # Search/Show commands
    "söyle", "anlat", "yaz",                    # Speak/Write commands
    "lütfen", "bana", "bize"                    # Polite/Target fillers
})

# ============================================================================
# UNIVERSAL STOP WORDS (Automatic composition via set union)
# ============================================================================
# This ensures consistency: if a word triggers a subtype, it MUST be removed
# from the search query to prevent false database matches.
# ============================================================================
UNIVERSAL_STOP_WORDS = (
    CONTEXT_REF_WORDS | 
    CLARIFICATION_WORDS | 
    QUESTION_WORDS | 
    GENERIC_WORDS |
    COMMAND_WORDS
)


class IntentType(Enum):
    SEARCH_PRODUCT = "SEARCH_PRODUCT"  # User wants to find a specific item
    LIST_CATALOG = "LIST_CATALOG"      # User asks "What genres do you have?"
    INFORMATIONAL = "INFORMATIONAL"    # Company info: vizyon, adres, iletisim (NOT product search)
    SOCIAL = "SOCIAL"                  # Casual chat, context ref, clarification needed
    UNKNOWN = "UNKNOWN"                # Cannot determine intent


# ============================================================================
# COMPANY SCOPE SIGNALS (SaaS Ready - Domain Agnostic)
# ============================================================================
# These signals indicate user is asking about the COMPANY, not products.
# When detected -> INFORMATIONAL intent, route to company_info table.
# NOTE: This should be loaded from config/DB in production (Sprint-2)
# ============================================================================
COMPANY_SCOPE_SIGNALS = frozenset({
    # Identity
    "vizyon", "vizyonunuz", "misyon", "misyonunuz",
    "kimsiniz", "kimsin", "nesiniz", "hakkında", "hakkınızda",
    # Location
    "adres", "adresiniz", "neredesiniz", "nerede", "konum", "lokasyon",
    # Contact
    "iletişim", "telefon", "mail", "email", "ulaşım", "ulaşabilirim",
    # Company
    "şirket", "firma", "kuruluş"
})

# Product signals - if present WITH company signals, treat as BUSINESS
PRODUCT_SIGNALS = frozenset({
    "fiyat", "kaç", "stok", "var mı", "ne kadar", "ücret",
    "satın", "sipariş", "al", "ürün", "şarkı", "albüm", "müzik"
})


@dataclass
class IntentResult:
    """
    Represents the extracted intent from user input.
    
    Attributes:
        intent: Primary intent classification
        query_term: Search term (None for wildcard or non-search intents)
        filters: Search filters (sort, price range, etc.)
        confidence: Confidence score (1.0 for rule-based)
        meta_data: Extensible payload for intent-specific context
                   Examples:
                   - SOCIAL: {"subtype": "context_ref" | "clarification" | "casual_chat"}
    """
    intent: IntentType
    query_term: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    meta_data: Dict[str, Any] = field(default_factory=dict)


class IntentExtractor:
    """
    Rule-based engine that converts raw user text into structured commands.
    Deterministic pattern matching using Semantic Groups.
    """
    
    def __init__(self):
        # Sorting/Filter keywords
        self.cheap_keywords = {"ucuz", "en uygun", "ekonomik", "hesaplı"}
        self.expensive_keywords = {"pahalı", "yüksek fiyat", "lüks"}
        
        # Catalog intent keywords (Legacy support, though semantics handle most)
        self.catalog_keywords = {"listele", "kategoriler", "türler", "tür", "çeşit", "tarz", "satıyorsunuz", "neler var", "hizmetler"}
        
        # Company scope signals (SaaS ready - load from config in production)
        self.company_signals = COMPANY_SCOPE_SIGNALS
        self.product_signals = PRODUCT_SIGNALS

        # DRY: Use module-level Universal Stop Words
        self.stop_words = UNIVERSAL_STOP_WORDS
    
    def classify(self, text: str) -> IntentResult:
        """
        Classify user input into structured intent via Semantic Analysis.
        
        Logic Flow:
        1. Normalize
        2. Detect sorting filters
        3. Check Catalog Intent
        4. Clean text (Semantic Stop Words)
        5. Determine Intent (Search vs Social)
        """
        original_text = text.strip()
        original_text_lower = original_text.lower()
        
        # === STEP 1: Detect Sorting Filters ===
        filters = self._extract_filters(original_text_lower)
        
        # === STEP 1.5: Check for INFORMATIONAL Intent (Company Scope) ===
        # PRIORITY: Company info queries should NOT hit product search
        # 
        # ARCHITECTURAL NOTE:
        # IntentExtractor only DETECTS intent type and provides minimal hints.
        # Topic extraction is delegated to KnowledgeResolver (Clean Architecture).
        if self._is_company_info_query(original_text_lower):
            return IntentResult(
                intent=IntentType.INFORMATIONAL,
                query_term=None,
                filters={},
                meta_data={
                    "scope_hint": "company",  # Hint only, not decision
                    "raw_text": original_text_lower  # Pass to resolver
                }
            )
        
        # === STEP 2: Check for Explicit Catalog Intent ===
        # Priority check for "list catalog" explicit lists
        if self._is_catalog_query(original_text_lower):
             return IntentResult(
                intent=IntentType.LIST_CATALOG,
                query_term=None,
                filters=filters
            )
        
        # === STEP 3: Clean Text (Extract potential search term) ===
        # Remove ALL semantic stop words to find 'meat' of the query
        cleaned_text = self._clean_query_text(original_text_lower)
        
        # === STEP 4: Determine Intent ===
        
        if not cleaned_text:
            # Query is empty after cleaning
            
            if filters:
                # WILDCARD SEARCH: "En pahalı ürün" -> Cleaned="" but filter=price_desc
                return IntentResult(
                    intent=IntentType.SEARCH_PRODUCT,
                    query_term=None,  # Wildcard
                    filters=filters
                )
            else:
                # SOCIAL: No query, no filters
                # Determine subtype via semantic grouping priority
                subtype = self._determine_social_subtype(original_text_lower)
                
                return IntentResult(
                    intent=IntentType.SOCIAL,
                    query_term=None,
                    filters={},
                    meta_data={"subtype": subtype}
                )
        else:
            # SEARCH_PRODUCT: Has content remaining
            # Example: "Metallica çal" -> "metallica"
            return IntentResult(
                intent=IntentType.SEARCH_PRODUCT,
                query_term=cleaned_text,
                filters=filters
            )
    
    def _clean_query_text(self, text: str) -> str:
        """
        Remove stop words using Semantic Groups.
        """
        # Tokenize and clean punctuation
        clean_text_step = re.sub(r'[^\w\s]', '', text)
        tokens = clean_text_step.split()
        
        # Filter out UNIVERSAL STOP WORDS
        filtered = [t for t in tokens if t not in self.stop_words]
        
        return " ".join(filtered).strip()

    def _determine_social_subtype(self, original_text: str) -> str:
        """
        Determine granular subtype for SOCIAL intent using Semantic Groups.
        Priority: context_ref > clarification > casual_chat
        """
        clean_text = re.sub(r'[^\w\s]', '', original_text)
        tokens = set(clean_text.split())
        
        # Priority 1: Context Reference
        if CONTEXT_REF_WORDS & tokens:
            return "context_ref"
        
        # Priority 2: Clarification Needed
        if CLARIFICATION_WORDS & tokens:
            return "clarification"
        
        # Priority 3: Casual Chat
        return "casual_chat"
    
    def _extract_filters(self, text: str) -> dict:
        """Detects sorting/filter modifiers."""
        filters = {}
        for keyword in self.cheap_keywords:
            if keyword in text:
                filters['sort'] = 'price_asc'
                break
        for keyword in self.expensive_keywords:
            if keyword in text:
                filters['sort'] = 'price_desc'
                break
        return filters
    
    def _is_catalog_query(self, text: str) -> bool:
        """Check for explicit LIST_CATALOG keywords."""
        # Note: "satıyorsunuz" handled via Clarification subtype usually, 
        # unless explicit list requested.
        # Keeping this simple for now.
        for keyword in self.catalog_keywords:
            if keyword in text:
                return True
        return False
    
    def _is_company_info_query(self, text: str) -> bool:
        """
        Check if query is asking about company info (INFORMATIONAL intent).
        
        Logic:
        1. Contains company scope signal (vizyon, adres, etc.)
        2. Does NOT contain product signals (fiyat, stok, etc.)
        
        Args:
            text: Normalized user input
            
        Returns:
            True if this is a company info query
        """
        has_company_signal = any(sig in text for sig in self.company_signals)
        has_product_signal = any(sig in text for sig in self.product_signals)
        
        # Company info ONLY if no product context
        return has_company_signal and not has_product_signal
    
    # =========================================================================
    # DEPRECATED: Topic extraction moved to TopicSignalProvider
    # =========================================================================
    # This method violated Single Responsibility Principle.
    # Topic extraction is now handled by KnowledgeResolver + TopicSignalProvider.
    # Keeping this commented for reference during migration.
    # =========================================================================
    
    # def _extract_company_topic(self, text: str) -> str:
    #     """
    #     DEPRECATED: Moved to TopicSignalProvider
    #     """
    #     pass
