from app.core.interfaces.query_normalizer import QueryNormalizer

class RuleBasedNormalizer(QueryNormalizer):
    """
    Concrete implementation of QueryNormalizer using configurable rules.
    1. Fixes typos (müdük -> müzik).
    2. Removes stopwords (flexible list).
    3. Preserves PROTECTED keywords (fiyat, nedir) for intent clarity.
    
    Performance: <1ms execution time (Pure Python).
    """
    
    # Typos & Misrecognitions (Static Default)
    DEFAULT_TYPOS = {
        "müdük": "müzik", "müzük": "müzik", "muzik": "müzik",
        "müdükler": "müzikler", "mülükler": "müzikler", "mücükler": "müzikler",
        "metalika": "metallica", "acdc": "ac/dc",
        "sanaçı": "sanatçı", "fiyatı": "fiyat"
    }
    
    # Default Stop Words (Can be overridden)
    DEFAULT_STOP_WORDS = {
        "bana", "getir", "göster", "listele", "kadar",
        "hakkında", "bilgi", "istiyorum", "var", "mı", "mi", "mu", 
        "lütfen", "hey", "melody", "merhaba", "selam"
    }
    
    # Default Protected Keywords (Service Domain Criticals)
    DEFAULT_PROTECTED = {
        "hizmet", "fiyat", "ücret", "ne", "nedir", "randevu", "saat", "kaç", "nerede"
    }
    
    # Generic domain words to strip (Context dependent)
    DEFAULT_DOMAIN_WORDS = {
        "müzik", "şarkı", "parça", "albüm", "çal", "dinle", "ürün", "kayıt"
    }

    def __init__(
        self, 
        stop_words: set = None, 
        protected_keywords: set = None,
        domain_words: set = None
    ):
        """
        Initialize with optional overrides for SaaS adaptability.
        """
        self.stop_words = stop_words if stop_words is not None else self.DEFAULT_STOP_WORDS
        self.protected_keywords = protected_keywords if protected_keywords is not None else self.DEFAULT_PROTECTED
        self.domain_words = domain_words if domain_words is not None else self.DEFAULT_DOMAIN_WORDS
        self.typo_map = self.DEFAULT_TYPOS

    def normalize(self, query: str) -> str:
        if not query:
            return ""
            
        # 1. Lowercase
        text = query.lower()
        
        # 2. Tokenize (simple split)
        tokens = text.split()
        normalized_tokens = []
        
        for token in tokens:
            # 3. Fix Typos
            clean_token = self.typo_map.get(token, token)
            
            # 4. Filter Logic (Smart Filter)
            # If it's a protected keyword, KEEP IT regardless of stop/domain lists
            if clean_token in self.protected_keywords:
                normalized_tokens.append(clean_token)
                continue
                
            # Otherwise check stop/domain lists
            if clean_token in self.stop_words or clean_token in self.domain_words:
                continue
                
            normalized_tokens.append(clean_token)
            
        # 5. Reassemble
        result = " ".join(normalized_tokens)
        
        # Fallback: If empty, return typo-fixed original to avoid silence
        if not result:
            return " ".join([self.typo_map.get(t, t) for t in tokens])
            
        return result
