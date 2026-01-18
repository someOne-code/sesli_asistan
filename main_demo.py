import asyncio
import sys
import os
import logging
import time

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
from app.core.services.assistant_service import AssistantService
from app.core.services.knowledge_resolver import KnowledgeResolver
from app.infrastructure.providers.default_signal_providers import DefaultScopeProvider, DefaultTopicProvider

# Configure Logging (Silence internals/debugs for demo clarity)
logging.basicConfig(level=logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def run_demo():
    print("========================================")
    print("ENTERPRISE SAAS AI AGENT – MULTI TENANT DEMO")
    print("========================================")
    print("")

    # 1. Bootstrap Infrastructure
    # ---------------------------
    
    # Database Repositories
    db_repo = HedefRepository(settings.DB_NAME)
    knowledge_repo = SqlKnowledgeRepository(settings.DB_NAME)
    
    # AI Service Selection based on Settings
    if settings.AI_PROVIDER == "gemini":
        from app.infrastructure.ai.gemini_service import GeminiAIService
        ai_service = GeminiAIService(settings.GEMINI_API_KEY)
    else:
        # Default to Groq
        from app.infrastructure.ai.groq_service import GroqAIService
        ai_service = GroqAIService(settings.GROQ_API_KEY)
    
    # Knowledge Components
    scope_provider = DefaultScopeProvider()
    topic_provider = DefaultTopicProvider()
    knowledge_resolver = KnowledgeResolver(scope_provider, topic_provider)
    
    # Initialize Tenant Context
    tenant_context = StaticTenantContext("initial_init")
    
    service = AssistantService(
        db_repo=db_repo,
        ai_service=ai_service,
        knowledge_resolver=knowledge_resolver,
        knowledge_repo=knowledge_repo,
        tenant_context=tenant_context
    )
    
    # Question text
    question_text = "Vizyonunuz nedir?"
    display_question = "What is your company vision?"

    # 2. Demo Flow
    # ---------------------------

    # --- Step 1: Tenant A (chinook_music) ---
    tenant_a = "chinook_music"
    
    # SWITCH TENANT
    # Note: Accessing private member for demo demonstration purposes only
    tenant_context._tenant_id = tenant_a 
    
    print("----------------------------------------")
    print(f"TENANT: {tenant_a}")
    print(f"QUESTION: {display_question}")
    
    response_a = await service.process_user_input(question_text, session_id="demo_session_a")
    print("RESPONSE:")
    print(response_a.get('ai_response', 'NO RESPONSE').strip())
    print("----------------------------------------")
    print("")
    
    time.sleep(1) # Prevent rate limiting

    # --- Step 2: Tenant B (otel_istanbul) ---
    tenant_b = "otel_istanbul"
    
    # SWITCH TENANT
    tenant_context._tenant_id = tenant_b
    
    print("----------------------------------------")
    print(f"TENANT: {tenant_b}")
    print(f"QUESTION: {display_question}")
    
    response_b = await service.process_user_input(question_text, session_id="demo_session_b")
    print("RESPONSE:")
    print(response_b.get('ai_response', 'NO RESPONSE').strip())
    print("----------------------------------------")

if __name__ == "__main__":
    asyncio.run(run_demo())
