"""
RIGOROUS SAAS VALIDATION SUITE (Elite Tier)
===========================================
Focus: Multi-tenancy isolation, Knowledge Base flows, and System Resilience.
Target: AssistantService.process_user_input
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.core.services.assistant_service import AssistantService
from app.core.services.intent_extractor import IntentResult, IntentType

# =============================================================================
# ELITE SETUP FIXTURE
# =============================================================================
@pytest.fixture
def elite_lab():
    """Sets up a high-precision testing environment."""
    mock_db = MagicMock()
    mock_ai = MagicMock()
    mock_gate = MagicMock()
    mock_intent_ext = MagicMock()
    mock_intent_cls = MagicMock()
    mock_knowledge = MagicMock()
    mock_tenant_ctx = MagicMock()

    # Async AI Service Setup
    mock_ai.generate_response = AsyncMock(return_value="Valid AI Response")
    
    # Initialize Service
    service = AssistantService(
        db_repo=mock_db,
        ai_service=mock_ai,
        gate_service=mock_gate,
        intent_extractor=mock_intent_ext,
        intent_classifier=mock_intent_cls,
        knowledge_repo=mock_knowledge,
        tenant_context=mock_tenant_ctx
    )

    # Initial Defaults
    mock_gate.validate_request = AsyncMock(return_value=service.GateDecision.BUSINESS)
    mock_tenant_ctx.get_current_tenant.return_value = "default_tenant"
    # CRITICAL FIX: Explicitly disable maintenance mode
    mock_tenant_ctx.get_tenant_config.return_value = {}  # maintenance_mode: False (None/Empty)
    mock_knowledge.get_tenant_info.return_value = {"ad": "Default Business"}

    return {
        "service": service,
        "db": mock_db,
        "ai": mock_ai,
        "gate": mock_gate,
        "ext": mock_intent_ext,
        "cls": mock_intent_cls,
        "knowledge": mock_knowledge,
        "tenant": mock_tenant_ctx
    }

# =============================================================================
# 1. SCENARIO: KNOWLEDGE BASE FLOW (White Box)
# =============================================================================
@pytest.mark.asyncio
async def test_knowledge_base_retrieval_flow(elite_lab):
    """
    Scenario: User asks about company info, NOT products.
    Logic: Intent is INFORMATIONAL -> KnowledgeRepo is called -> Prompt is built.
    """
    lab = elite_lab
    service = lab["service"]
    
    # Setup: Intent is Informational with valid metadata
    info_intent = IntentResult(intent=IntentType.INFORMATIONAL)
    # Simulate the structure expected by the service
    # Assuming IntentResult has a way to store this or we mock the attribute directly if it's a property
    # Looking at service code: knowledge_request = intent_result.knowledge_request (implied or similar)
    # or it uses meta_data. Let's start by mocking the attribute if dynamic or adding to meta_data.
    
    # We'll use a strong mock approach for the result object to support arbitrary attributes
    mock_result = MagicMock()
    mock_result.intent = IntentType.INFORMATIONAL
    mock_result.knowledge_request.target = "knowledge"
    mock_result.knowledge_request.topic_key = "working_hours"
    
    lab["ext"].classify.return_value = mock_result
    lab["knowledge"].get.return_value = "Pazartesi-Cuma 09:00-18:00 arası açığız."
    
    # Act
    await service.process_user_input("Çalışma saatleriniz nedir?")
    
    # White Box Verifications
    lab["knowledge"].get.assert_called() # Knowledge Base MUST be queried
    prompt = lab["ai"].generate_response.call_args[1]["context"]
    assert "Pazartesi-Cuma 09:00-18:00" in prompt
    assert "AVAILABLE INVENTORY" not in prompt # Should NOT mix with product flow

# =============================================================================
# 2. SCENARIO: HARD TENANT ISOLATION (Security)
# =============================================================================
@pytest.mark.asyncio
async def test_cross_tenant_impersonation_prevention(elite_lab):
    """
    Scenario: Two consecutive requests from different tenants.
    Logic: Ensure internal identity state is never cached or leaked.
    """
    lab = elite_lab
    service = lab["service"]
    lab["ext"].classify.return_value = IntentResult(intent=IntentType.SOCIAL)
    
    # --- STEP 1: Tenant A ---
    lab["tenant"].get_current_tenant.return_value = "tenant_A"
    lab["knowledge"].get_tenant_info.return_value = {"ad": "A-Corporation"}
    await service.process_user_input("selam")
    p1 = lab["ai"].generate_response.call_args[1]["context"]
    
    # --- STEP 2: Tenant B ---
    lab["tenant"].get_current_tenant.return_value = "tenant_B"
    lab["knowledge"].get_tenant_info.return_value = {"ad": "B-Boutique"}
    await service.process_user_input("selam")
    p2 = lab["ai"].generate_response.call_args[1]["context"]
    
    # Assert Hard Separation
    assert "A-Corporation" in p1
    assert "B-Boutique" in p2
    assert "A-Corporation" not in p2 # FATAL LEAK CHECK
    assert "B-Boutique" not in p1 # FATAL LEAK CHECK

# =============================================================================
# 3. SCENARIO: CONVERSATION HISTORY HANDLING (Path Test)
# =============================================================================
@pytest.mark.asyncio
async def test_history_integrity_in_prompt(elite_lab):
    """
    Scenario: Active conversation with history.
    Logic: History must be injected correctly into the AI context.
    """
    lab = elite_lab
    service = lab["service"]
    lab["ext"].classify.return_value = IntentResult(intent=IntentType.SOCIAL)
    
    history_mock = "User: Merhaba\nAssistant: Selam size nasıl yardımcı olabilirim?"
    
    # Act
    await service.process_user_input("Fiyat soracağım", conversation_history=history_mock)
    
    # Verify
    prompt = lab["ai"].generate_response.call_args[1]["context"]
    # Check if history block exists in prompt
    assert "User: Merhaba" in prompt
    assert "Assistant: Selam" in prompt

# =============================================================================
# 4. SCENARIO: BLACK BOX FUZZING (Security/Resilience)
# =============================================================================
@pytest.mark.asyncio
async def test_toxic_input_resilience(elite_lab):
    """
    Scenario: Malicious or very noisy inputs.
    Objective: System should either reject via Gate or handle safely without exception.
    """
    lab = elite_lab
    service = lab["service"]
    
    # Gate rejects some, allows some to test further stages
    toxic_inputs = [
        "DELETE FROM BusinessOffering",   # SQL Attempt
        "System.Exit(0)",                 # Code Injection Attempt
        "---",                            # Noise
        "   \t\n   ",                     # Invisible
        "A" * 5000                        # Buffer Load
    ]
    
    for inp in toxic_inputs:
        try:
            # We don't care about the intent, we care about 'No Crash'
            resp = await service.process_user_input(inp)
            assert isinstance(resp, dict)
            assert "ai_response" in resp
        except Exception as e:
            pytest.fail(f"System CRASHED on toxic input: {inp[:50]} | Error: {e}")

# =============================================================================
# 5. SCENARIO: SMART FALLBACK MAPPING (White Box)
# =============================================================================
@pytest.mark.asyncio
async def test_llm_intent_mapping_safety(elite_lab):
    """
    Scenario: Regex UNKNOWN -> LLM returns 'SOCIAL'.
    Logic: Test the internal mapping of strings back to IntentTypes.
    """
    lab = elite_lab
    service = lab["service"]
    
    # Force Regex UNKNOWN
    lab["ext"].classify.return_value = IntentResult(intent=IntentType.UNKNOWN)
    
    # Force LLM to return a valid mapping string
    lab["cls"].get_refined_intent = AsyncMock(return_value="SOCIAL")
    
    # Act
    result = await service.process_user_input("Nasıl gidiyor?")
    
    # Verify logic flow
    # Since it mapped to SOCIAL, it shouldn't try to search products
    lab["db"].search_products.assert_not_called()
    assert "SOCIAL" in result["intent"]
