import asyncio
import sys
import os

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.services.assistant_service import AssistantService
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.ai.groq_service import GroqAIService
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
from app.core.config import settings
from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer
from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository

async def debug_flow():
    print("\n🚀 DEBUG FLOW STARTING...\n")
    
    # 1. Setup Dependencies
    print("1. Initializing Dependencies...")
    db = HedefRepository(settings.DB_NAME)
    ai = GroqAIService(settings.GROQ_API_KEY)
    
    # Teach schema to AI (Important!)
    schema = db.get_safe_schema_summary()
    ai.set_db_schema(schema)
    print(f"   AI Schema Set: {len(schema)} chars")
    
    norm = RuleBasedNormalizer()
    know = SqlKnowledgeRepository(settings.DB_NAME)
    ctx = StaticTenantContext("berber_ahmet")
    
    # 2. Initialize Service with ALL components explicit if possible
    print("2. Initializing AssistantService...")
    service = AssistantService(
        db_repo=db, 
        ai_service=ai, 
        normalizer=norm,
        knowledge_repo=know,
        tenant_context=ctx
    )
    
    # 3. Process Input
    user_text = "Merhaba, saç kesimi ne kadar?"
    print(f"\n3. Processing Input: '{user_text}'")
    
    try:
        result = await service.process_user_input(user_text, session_id="debug_session_1")
        
        print("\n✅ RESULT RECEIVED:")
        print(f"   Intent: {result.get('intent')}")
        print(f"   AI Response: {result.get('ai_response')}")
        print(f"   Context Used: {result.get('context_used')[:100]}...") # Truncated
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_flow())
