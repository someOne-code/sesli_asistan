from typing import List, Dict, Optional
import json
from datetime import datetime, timedelta
from config import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory conversation storage.")


class ConversationMemory:
    """
    Manages conversation history for context-aware responses.
    Supports both Redis (persistent) and in-memory (fallback) storage.
    """
    
    def __init__(self, redis_url: Optional[str] = None, session_id: str = "default", max_turns: int = 10):
        self.session_id = session_id
        self.max_turns = max_turns
        self.redis_client = None
        
        # Try to connect to Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info(f"✅ Redis connected for session: {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory storage.")
                self.redis_client = None
        
        # Fallback: in-memory storage
        self._memory: List[Dict] = []
    
    def add_turn(self, user_text: str, ai_response: str) -> None:
        """Add a conversation turn to memory"""
        turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user_text,
            "assistant": ai_response
        }
        
        if self.redis_client:
            self._add_to_redis(turn)
        else:
            self._add_to_memory(turn)
    
    def _add_to_redis(self, turn: Dict) -> None:
        """Add turn to Redis"""
        try:
            key = f"conversation:{self.session_id}"
            
            # Get existing conversation
            conversation = self.redis_client.get(key)
            if conversation:
                turns = json.loads(conversation)
            else:
                turns = []
            
            # Add new turn
            turns.append(turn)
            
            # Keep only last N turns
            turns = turns[-self.max_turns:]
            
            # Save back to Redis with expiration (30 minutes)
            self.redis_client.setex(
                key,
                timedelta(minutes=30),
                json.dumps(turns)
            )
        except Exception as e:
            logger.error(f"Error adding to Redis: {e}")
    
    def _add_to_memory(self, turn: Dict) -> None:
        """Add turn to in-memory storage"""
        self._memory.append(turn)
        
        # Keep only last N turns
        if len(self._memory) > self.max_turns:
            self._memory = self._memory[-self.max_turns:]
    
    def get_context(self, last_n: Optional[int] = None) -> str:
        """
        Get conversation context as a formatted string.
        
        Args:
            last_n: Number of recent turns to include (default: all)
        
        Returns:
            Formatted conversation history
        """
        if self.redis_client:
            turns = self._get_from_redis()
        else:
            turns = self._memory.copy()
        
        if not turns:
            return ""
        
        # Get last N turns
        if last_n:
            turns = turns[-last_n:]
        
        # Format as conversation
        context_lines = []
        for turn in turns:
            context_lines.append(f"User: {turn['user']}")
            context_lines.append(f"Assistant: {turn['assistant']}")
        
        return "\n".join(context_lines)
    
    def _get_from_redis(self) -> List[Dict]:
        """Get conversation from Redis"""
        try:
            key = f"conversation:{self.session_id}"
            conversation = self.redis_client.get(key)
            if conversation:
                return json.loads(conversation)
            return []
        except Exception as e:
            logger.error(f"Error getting from Redis: {e}")
            return []
    
    def get_last_turn(self) -> Optional[Dict]:
        """Get the most recent conversation turn"""
        if self.redis_client:
            turns = self._get_from_redis()
        else:
            turns = self._memory
        
        return turns[-1] if turns else None
    
    def get_all_turns(self) -> List[Dict]:
        """Get all conversation turns"""
        if self.redis_client:
            return self._get_from_redis()
        return self._memory.copy()
    
    def clear(self) -> None:
        """Clear conversation history"""
        if self.redis_client:
            try:
                key = f"conversation:{self.session_id}"
                self.redis_client.delete(key)
                logger.info(f"🗑️ Redis conversation cleared for session: {self.session_id}")
            except Exception as e:
                logger.error(f"Error clearing Redis: {e}")
        else:
            self._memory.clear()
            logger.info(f"🗑️ Memory cleared for session: {self.session_id}")
    
    def count_turns(self) -> int:
        """Get number of conversation turns"""
        if self.redis_client:
            turns = self._get_from_redis()
            return len(turns)
        return len(self._memory)
    
    def has_context(self) -> bool:
        """Check if there's any conversation history"""
        return self.count_turns() > 0
    
    def get_summary(self) -> str:
        """Get a brief summary of the conversation"""
        turns = self.get_all_turns()
        if not turns:
            return "No conversation history."
        
        first_turn = turns[0]
        last_turn = turns[-1]
        turn_count = len(turns)
        
        return f"Conversation with {turn_count} turns. Started: {first_turn['timestamp']}, Last: {last_turn['timestamp']}"


class SessionManager:
    """Manages multiple conversation sessions"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.sessions: Dict[str, ConversationMemory] = {}
    
    def get_session(self, session_id: str) -> ConversationMemory:
        """Get or create a conversation session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory(
                redis_url=self.redis_url,
                session_id=session_id
            )
            logger.info(f"📝 Created new session: {session_id}")
        
        return self.sessions[session_id]
    
    def delete_session(self, session_id: str) -> None:
        """Delete a conversation session"""
        if session_id in self.sessions:
            self.sessions[session_id].clear()
            del self.sessions[session_id]
            logger.info(f"🗑️ Deleted session: {session_id}")
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self.sessions.keys())
    
    def clear_all_sessions(self) -> None:
        """Clear all sessions"""
        for session_id in list(self.sessions.keys()):
            self.delete_session(session_id)
        logger.info("🗑️ All sessions cleared")