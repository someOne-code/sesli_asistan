import asyncio
import os
from app.core.config import settings
from app.infrastructure.database.repository import SqliteMusicRepository
from app.infrastructure.ai.groq_service import GroqAIService
from app.core.services.assistant_service import AssistantService

async def main():
    print("Testing AI Logic...")
    
    # Init dependencies
    db_repo = SqliteMusicRepository(db_url="hedef.db")
    ai_service = GroqAIService(api_key=settings.GROQ_API_KEY)
    
    # Teach schema
    safe_schema = db_repo.get_safe_schema_summary()
    ai_service.set_db_schema(safe_schema)
    
    service = AssistantService(db_repo, ai_service)
    
    # Test Cases
    test_inputs = [
        "Selam",
        "Müslüm Gürses çal",
        "Ne satıyorsun?",
        "Tarkan var mı?"
    ]
    
    history = ""
    
    for text in test_inputs:
        print(f"\n--- User: {text} ---")
        result = await service.process_user_input(text, conversation_history=history)
        response = result["ai_response"]
        print(f"AI: {response}")
        print(f"Intent: {result['intent']}")
        print(f"Context: {result.get('context_used', 'N/A')}")
        
        # Simulate history update
        history += f"User: {text}\nAI: {response}\n"

if __name__ == "__main__":
    asyncio.run(main())
