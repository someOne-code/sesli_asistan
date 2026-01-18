import asyncio
import time
from app.infrastructure.database.repository import SqliteMusicRepository
from app.infrastructure.ai.groq_service import GroqAIService
from app.core.services.assistant_service import AssistantService
from app.core.config import settings

# Mock memory
class MockMemory:
    def add_turn(self, user, ai):
        print(f"\n[Memory] Updated: User='{user}', AI='{ai[:50]}...'")
    def get_context(self):
        return ""

async def main():
    print("Testing Streaming Pipeline...")
    
    # Init
    db_repo = SqliteMusicRepository(db_url="hedef.db")
    
    # Ensure AI service has schema
    ai_service = GroqAIService(api_key=settings.GROQ_API_KEY)
    ai_service.set_db_schema(db_repo.get_safe_schema_summary())
    
    service = AssistantService(db_repo, ai_service)
    
    # Test Input
    user_text = "Bana kısa bir masal anlat."
    print(f"User: {user_text}")
    print("Request sent. Waiting for stream...")
    
    t_start = time.time()
    
    stream = service.process_user_input_stream(user_text, "test_session", "", MockMemory())
    
    chunk_count = 0
    first = True
    bytes_total = 0
    
    async for chunk in stream:
        chunk_count += 1
        bytes_total += len(chunk)
        if first:
            elapsed = time.time() - t_start
            print(f"✅ FIRST AUDIO CHUNK received after: {elapsed * 1000:.2f} ms")
            first = False
            
    total_time = time.time() - t_start
    print(f"Stream finished. Total chunks: {chunk_count}, Total bytes: {bytes_total}")
    print(f"Total duration: {total_time:.2f}s")
    
    if chunk_count > 0:
        print("✅ SUCCESS: Stream yielded audio data.")
    else:
        print("❌ FAILURE: No audio chunks received.")

if __name__ == "__main__":
    asyncio.run(main())
