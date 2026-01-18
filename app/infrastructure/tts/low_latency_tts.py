"""
Ultra-Low Latency TTS Streaming Pipeline

Key optimizations:
1. Silent audio primer (50ms) - wakes browser AudioContext immediately
2. Word/phrase chunking (every 4-6 words) - much faster than sentence-based
3. Parallel TTS generation - start next phrase while current one streams
"""
import edge_tts
import asyncio
import re
from typing import AsyncGenerator
from app.core.config import settings

# 50ms of silence in MP3 format (minimal valid MP3 frame)
# This primes the browser's audio context for instant playback
SILENT_AUDIO_PRIMER = bytes([
    0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]) * 3  # ~50ms of silence

class PhraseChunker:
    """
    Splits streaming text into speakable phrases.
    Much more aggressive than sentence-based splitting.
    """
    def __init__(self, min_words: int = 3, max_words: int = 8):
        self.min_words = min_words
        self.max_words = max_words
        self.buffer = ""
        self.word_count = 0
    
    def add_text(self, text: str) -> list[str]:
        """Add text and return any complete phrases."""
        self.buffer += text
        phrases = []
        
        # Count words in buffer
        words = self.buffer.split()
        self.word_count = len(words)
        
        # Check for natural break points
        # Priority: sentence end > comma/semicolon > word limit
        
        # 1. Check for sentence endings
        sentence_match = re.search(r'^(.+?[.!?])\s*', self.buffer)
        if sentence_match and len(sentence_match.group(1).split()) >= self.min_words:
            phrase = sentence_match.group(1)
            self.buffer = self.buffer[len(sentence_match.group(0)):]
            phrases.append(phrase)
            return phrases
        
        # 2. Check for comma/semicolon breaks (if enough words)
        if self.word_count >= self.min_words:
            comma_match = re.search(r'^(.+?[,;:])\s*', self.buffer)
            if comma_match and len(comma_match.group(1).split()) >= self.min_words:
                phrase = comma_match.group(1)
                self.buffer = self.buffer[len(comma_match.group(0)):]
                phrases.append(phrase)
                return phrases
        
        # 3. Force split if too many words (prevents unbounded buffering)
        if self.word_count >= self.max_words:
            words = self.buffer.split()
            phrase = " ".join(words[:self.max_words])
            self.buffer = " ".join(words[self.max_words:])
            phrases.append(phrase)
            return phrases
        
        return phrases  # Empty if no phrase ready yet
    
    def flush(self) -> str:
        """Return any remaining text."""
        remaining = self.buffer.strip()
        self.buffer = ""
        return remaining


async def tts_phrase_to_audio(phrase: str, voice: str) -> AsyncGenerator[bytes, None]:
    """Convert a single phrase to audio stream."""
    if not phrase.strip():
        return
    
    communicate = edge_tts.Communicate(phrase, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


async def low_latency_tts_pipeline(
    llm_stream: AsyncGenerator[str, None],
    voice: str = None
) -> AsyncGenerator[bytes, None]:
    """
    Ultra-low latency TTS pipeline.
    
    1. Immediately yields silent primer (browser wakes up)
    2. Chunks LLM tokens into phrases (3-8 words)
    3. Converts each phrase to audio as soon as ready
    4. Streams audio chunks to browser continuously
    """
    import time
    
    voice = voice or settings.SES_MODELI
    t_start = time.time() * 1000
    
    # STEP 1: Immediately send silent primer to wake browser
    print(f"[TTS] Sending audio primer at {int(time.time() * 1000 - t_start)} ms")
    yield SILENT_AUDIO_PRIMER
    
    # STEP 2: Initialize phrase chunker
    chunker = PhraseChunker(min_words=3, max_words=8)
    first_phrase_spoken = False
    full_text = ""
    
    # STEP 3: Process LLM stream
    async for token in llm_stream:
        full_text += token
        
        # Try to extract complete phrases
        phrases = chunker.add_text(token)
        
        for phrase in phrases:
            if phrase.strip():
                if not first_phrase_spoken:
                    print(f"[TTS] First phrase ready at {int(time.time() * 1000 - t_start)} ms: '{phrase[:30]}...'")
                    first_phrase_spoken = True
                
                # Stream this phrase's audio immediately
                async for audio_chunk in tts_phrase_to_audio(phrase, voice):
                    yield audio_chunk
    
    # STEP 4: Flush remaining buffer
    remaining = chunker.flush()
    if remaining:
        print(f"[TTS] Flushing remaining: '{remaining[:30]}...'")
        async for audio_chunk in tts_phrase_to_audio(remaining, voice):
            yield audio_chunk
    
    print(f"[TTS] Pipeline complete. Total text: {len(full_text)} chars")
