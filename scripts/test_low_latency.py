"""
Test script for ultra-low latency TTS pipeline.
Measures time-to-first-byte (TTFB) including audio primer.
"""
import asyncio
import time
from app.infrastructure.database.repository import SqliteMusicRepository
from app.infrastructure.ai.groq_service import GroqAIService
from app.core.services.assistant_service import AssistantService
from app.core.config import settings

class MockMemory:
    def add_turn(self, user, ai):
        print(f"\n[Memory] Updated with {len(ai)} chars")
    def get_context(self):
        return ""

async def main():
    print("=" * 60)
    print("ULTRA-LOW LATENCY TTS PIPELINE TEST")
    print("=" * 60)
    
    # Init
    db_repo = SqliteMusicRepository(db_url="hedef.db")
    ai_service = GroqAIService(api_key=settings.GROQ_API_KEY)
    ai_service.set_db_schema(db_repo.get_safe_schema_summary())
    service = AssistantService(db_repo, ai_service)
    
    # Test input
    user_text = "Bana kısa bir hikaye anlat."
    print(f"\nUser: {user_text}")
    print("Starting stream...\n")
    
    t_start = time.time()
    
    stream = service.process_user_input_stream(
        user_text, 
        "test_session", 
        "", 
        MockMemory()
    )
    
    chunk_count = 0
    bytes_total = 0
    first_chunk_time = None
    
    async for chunk in stream:
        chunk_count += 1
        bytes_total += len(chunk)
        
        if first_chunk_time is None:
            first_chunk_time = (time.time() - t_start) * 1000
            print(f"✅ FIRST AUDIO CHUNK (primer) at: {first_chunk_time:.0f} ms")
        
        # Log every 10th chunk for progress
        if chunk_count % 10 == 0:
            print(f"   Chunk {chunk_count}: {bytes_total} bytes total...")
    
    total_time = (time.time() - t_start) * 1000
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS:")
    print(f"  - Time to first byte: {first_chunk_time:.0f} ms")
    print(f"  - Total chunks: {chunk_count}")
    print(f"  - Total bytes: {bytes_total}")
    print(f"  - Total time: {total_time:.0f} ms")
    print(f"{'=' * 60}")
    
    if first_chunk_time and first_chunk_time < 200:
        print("🎉 SUCCESS: Audio primer delivered in < 200ms!")
        print("   Browser will start audio context immediately.")
    else:
        print("⚠️ WARNING: First chunk took > 200ms")
        print("   This may indicate an issue with the primer.")

if __name__ == "__main__":
    asyncio.run(main())
