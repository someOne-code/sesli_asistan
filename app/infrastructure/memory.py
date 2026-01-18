import redis
import json
from typing import List, Dict, Optional, Any
from app.core.config import settings, logger
from datetime import datetime

class VoiceState:
    """State machine states - STRICT enforcement"""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    
    VALID_TRANSITIONS = {
        IDLE: [LISTENING],
        LISTENING: [THINKING],
        THINKING: [SPEAKING],
        SPEAKING: [LISTENING]
    }

class ConversationMemory:
    def __init__(self, redis_url: Optional[str] = None, session_id: str = "default_session"):
        self.session_id = session_id
        self.use_redis = False
        self.redis_client = None
        self.local_memory: List[Dict[str, str]] = []
        self._has_greeted = False
        self._state = VoiceState.IDLE
        self._state_change_time = datetime.now()

        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                self.use_redis = True
                logger.info(f"Connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to in-memory.")
                self.use_redis = False

    @property
    def has_greeted(self) -> bool:
        return self._has_greeted
    
    def mark_greeted(self):
        self._has_greeted = True

    def is_first_message(self) -> bool:
        if self.use_redis:
            try:
                count = self.redis_client.llen(f"chat:{self.session_id}")
                return count == 0
            except:
                return len(self.local_memory) == 0
        return len(self.local_memory) == 0

    # ========== STATE MACHINE ==========
    
    def get_state(self) -> str:
        return self._state
    
    def set_state(self, new_state: str) -> bool:
        """Validate and set state. Returns True if allowed."""
        allowed = VoiceState.VALID_TRANSITIONS.get(self._state, [])
        if new_state not in allowed:
            logger.warning(f"[STATE] INVALID TRANSITION: {self._state} → {new_state}")
            return False
        
        logger.info(f"[STATE] {self._state} → {new_state}")
        self._state = new_state
        self._state_change_time = datetime.now()
        return True
    
    def can_accept_input(self) -> bool:
        """Only accept input in LISTENING state."""
        return self._state == VoiceState.LISTENING
    
    def force_listening(self):
        """Force state to LISTENING (used by watchdog)."""
        logger.warning(f"[STATE] FORCE RESET: {self._state} → LISTENING")
        self._state = VoiceState.LISTENING
        self._state_change_time = datetime.now()

    # ========== CONVERSATION ==========

    def add_turn(self, user_text: str, ai_text: str):
        turn = {"user": user_text, "ai": ai_text}
        
        if self.use_redis:
            try:
                self.redis_client.rpush(f"chat:{self.session_id}", json.dumps(turn))
                self.redis_client.ltrim(f"chat:{self.session_id}", -10, -1)
            except Exception as e:
                logger.error(f"Redis write error: {e}")
        else:
            self.local_memory.append(turn)
            if len(self.local_memory) > 10:
                self.local_memory.pop(0)

    def get_context(self) -> str:
        history = []
        if self.use_redis:
            try:
                raw_list = self.redis_client.lrange(f"chat:{self.session_id}", 0, -1)
                history = [json.loads(item) for item in raw_list]
            except Exception as e:
                logger.error(f"Redis read error: {e}")
                return ""
        else:
            history = self.local_memory

        if not history:
            return ""
        
        formatted_context = ""
        for i, turn in enumerate(history, 1):
            formatted_context += f"[{i}] Kullanıcı: {turn['user']}\n[{i}] Sen: {turn['ai']}\n\n"
        
        return formatted_context.strip()

    def clear(self):
        self._has_greeted = False
        self._state = VoiceState.IDLE
        if self.use_redis:
            self.redis_client.delete(f"chat:{self.session_id}")
            self.redis_client.delete(f"dialogue:{self.session_id}")
        else:
            self.local_memory.clear()
            self._dialogue_state = None  # Local cache

    # ========== DIALOGUE STATE PERSISTENCE (Phase 1) ==========
    
    def get_dialogue_state(self) -> Dict[str, Any]:
        """Retrieve persisted dialogue state and slots"""
        default_state = {"state": "initial", "slots": {}, "turn_count": 0}
        
        if self.use_redis:
            try:
                data = self.redis_client.get(f"dialogue:{self.session_id}")
                return json.loads(data) if data else default_state
            except Exception as e:
                logger.error(f"Redis persist error: {e}")
                return default_state
        else:
            return getattr(self, "_dialogue_state", default_state)
            
    def save_dialogue_state(self, state_data: Dict[str, Any]):
        """Persist dialogue state"""
        if self.use_redis:
            try:
                self.redis_client.set(f"dialogue:{self.session_id}", json.dumps(state_data))
            except Exception as e:
                logger.error(f"Redis save error: {e}")
        else:
            self._dialogue_state = state_data
