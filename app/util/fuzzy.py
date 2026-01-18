"""
Fuzzy matching utility for voice recognition corrections.
Handles common speech-to-text errors in Turkish music queries.
"""

# Common misrecognitions -> correct term
FUZZY_MAP = {
    # Müzik variations (comprehensive)
    "mücük": "müzik",
    "müçik": "müzik", 
    "muzik": "müzik",
    "musuk": "müzik",
    "mucuk": "müzik",
    "müdük": "müzik",
    "mülük": "müzik",
    "müzük": "müzik",
    "müdik": "müzik",
    "mülik": "müzik",
    "müdükler": "müzikler",
    "mülükler": "müzikler",
    "müzükler": "müzikler",
    "mücükler": "müzikler",
    "müçikler": "müzikler",
    "müdikler": "müzikler",
    "mülikler": "müzikler",
    "müzikleriniz": "müzikler",
    "müdükleriniz": "müzikler",
    "mülükleriniz": "müzikler",
    
    # Şarkı variations
    "şarkü": "şarkı",
    "şarki": "şarkı",
    "sarkı": "şarkı",
    "sarki": "şarkı",
    "şarkılar": "şarkılar",
    
    # Albüm variations
    "albüm": "albüm",
    "album": "albüm",
    "albun": "albüm",
    
    # Sanatçı variations
    "sanaçı": "sanatçı",
    "sanatcı": "sanatçı",
    "sanatci": "sanatçı",
    
    # Artist names
    "kuin": "queen",
    "kuyn": "queen",
    "quin": "queen",
    "metalika": "metallica",
    "mettalica": "metallica",
    "acdc": "ac/dc",
    "ac dc": "ac/dc",
    
    # Tür/Genre variations
    "tir": "tür",
    "tur": "tür",
    
    # Common phrases
    "tüm müzikler": "tüm müzikler",
    "bütün müzikler": "tüm müzikler",
    "tüm şarkılar": "tüm şarkılar",
    "bütün şarkılar": "tüm şarkılar",
}

# Phrases that trigger LIST_ALL intent
LIST_ALL_TRIGGERS = [
    "tüm müzik",
    "tüm şarkı",
    "tüm albüm",
    "bütün müzik",
    "bütün şarkı",
    "bütün albüm",
    "tüm ürün",
    "bütün ürün",
    # "ne tür müzik" -> Moved to Catalog Intent logic
    "hangi müzik",
    "hangi şarkı",
    "müzikleriniz",
    "şarkılarınız",
    "albümleriniz",
    "kataloğunuz",
    "neler var",
    "ne var",
]

def normalize_query(text: str) -> str:
    """
    Normalizes voice-transcribed text by fixing common misrecognitions.
    Returns the corrected text.
    """
    result = text.lower()
    
    # Apply fuzzy replacements
    for wrong, correct in FUZZY_MAP.items():
        if wrong in result:
            result = result.replace(wrong, correct)
    
    return result

def is_list_all_query(text: str) -> bool:
    """
    Checks if the query is asking for all products/catalog.
    Returns True if it's a LIST_ALL intent.
    """
    normalized = normalize_query(text.lower())
    
    for trigger in LIST_ALL_TRIGGERS:
        if trigger in normalized:
            return True
    
    return False
