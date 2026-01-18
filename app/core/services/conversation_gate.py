"""
Conversation Gate (Behavioral, Language-Agnostic).
Classifies interaction PURPOSE, not content.
Zero hardcoded keyword lists. Logic is injected via Config.
"""

from enum import Enum
from typing import Set, Optional
from dataclasses import dataclass, field

class GateDecision(Enum):
    BUSINESS = "BUSINESS"   # User is making a business request
    SOCIAL = "SOCIAL"       # User is engaging in phatic/greeting interaction
    OFF_TOPIC = "OFF_TOPIC" # User is asking something outside the operator's role
    BLOCKED = "BLOCKED"     # User is asking something illegal/harmful

@dataclass
class GateConfig:
    """
    Vocabulary Injection.
    Separates LANGUAGE from LOGIC.
    To add a new language, modify the config, NOT the Gate.
    """
    # BLOCKED keywords - Safety First (HIGHEST PRIORITY)
    blocked_particles: Set[str] = field(default_factory=lambda: {
        "bomba", "silah", "uyuşturucu", "öldür", "saldır",
        "intihar", "patla", "hack", "illegal", "yasadışı"
    })

    # BUSINESS keywords - Music Store domain (SECONDARY PRIORITY)
    business_particles: Set[str] = field(default_factory=lambda: {
        "fiyat", "ücret", "kaç para", "stok", "var mı", "ne kadar",
        "çal", "oynat", "dinle", "albüm", "şarkı", "sanatçı", 
        "kim", "pahalı", "ucuz", "tür", "listele", "getir",
        "müzik", "bul", "ara", "kategori", "genre",
        "saç", "sakal", "kesim", "tıraş", "randevu", "saat", "uygun"
    })
    
    # SOCIAL keywords - Phatic/Greeting/Identity/Audio Check (SECONDARY PRIORITY)
    social_particles: Set[str] = field(default_factory=lambda: {
        "merhaba", "selam", "naber", "nasılsın", "günaydın", 
        "iyi geceler", "hoşçakal", "baybay", "hey", "hi", "hello",
        "nasıl gidiyor", "gidiyor",
        # Audio Checks (Identity moved to agent_focus for OFF_TOPIC)
        "duyuyor", "duyabiliyor", "geliyor mu", "orada mısın"
    })
    
    # Agent Focus - OFF_TOPIC triggers
    # Personal questions about the agent's identity/personal life
    agent_focus_particles: Set[str] = field(default_factory=lambda: {
        "yaşın", "sevdiğin", "sevgilin", "annen", "baban", "maaşın",
        "adın", "kimsin", "sen nesin", "nerelisin"  # Identity questions -> OFF_TOPIC
    })
    
    # Task Framing - treated as BUSINESS
    framing_particles: Set[str] = field(default_factory=lambda: {
        "soracağım", "sorabilir", "alabilir", "yardımcı", "bilgi"
    })

class ConversationGate:
    """
    A stateless, deterministic gate that classifies interaction purpose.
    Uses PRIORITY INVERSION: Business keywords override Social keywords.
    """

    def __init__(self, config: Optional[GateConfig] = None):
        self.config = config or GateConfig()

    def evaluate(self, text: str) -> GateDecision:
        """
        Classifies user input using PRIORITY-BASED keyword matching.
        
        Priority Order:
        1. BLOCKED (Highest) - Safety first
        2. BUSINESS (High) - Any business keyword found
        3. FRAMING -> BUSINESS - User preparing to ask
        4. SOCIAL (Identity/Greeting) - Explicit social Interaction
        5. AGENT FOCUS -> OFF_TOPIC - Irrelevant personal questions
        6. Default -> BUSINESS (Unknown = actionable)
        """
        normalized = text.strip().lower()

        # === PRIORITY 1: BLOCKED Intent (Safety First) ===
        if self._contains_any_particle(normalized, self.config.blocked_particles):
            return GateDecision.BLOCKED
        
        # === PRIORITY 2: BUSINESS Intent (High Priority) ===
        if self._contains_any_particle(normalized, self.config.business_particles):
            return GateDecision.BUSINESS
        
        # === PRIORITY 3: Task Framing -> BUSINESS ===
        if self._contains_any_particle(normalized, self.config.framing_particles):
            return GateDecision.BUSINESS
            
        # === PRIORITY 3: SOCIAL Intent (Greeting & Identity) ===
        # "Adın ne" -> SOCIAL (Now higher priority than OFF_TOPIC)
        if self._contains_any_particle(normalized, self.config.social_particles):
            return GateDecision.SOCIAL
        
        # === PRIORITY 4: Agent Focus -> OFF_TOPIC ===
        # "Sevgilin var mı?" -> OFF_TOPIC
        if self._contains_any_particle(normalized, self.config.agent_focus_particles):
            return GateDecision.OFF_TOPIC
        
        # === PRIORITY 5: Default -> BUSINESS ===
        return GateDecision.BUSINESS

    def _contains_any_particle(self, text: str, particles: Set[str]) -> bool:
        """
        Checks if any particle exists in the text.
        Handles both single words and multi-word phrases.
        """
        for particle in particles:
            if particle in text:
                return True
        return False
