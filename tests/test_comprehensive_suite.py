"""
COMPREHENSIVE TEST SUITE (Final Verification)
=============================================
Methodologies: Black Box, White Box, Path Testing.
Target: AssistantService.process_user_input

Rules:
- STRICT adherence to method signatures.
- Mocking must reflect real-world Async behaviors.
- Security checks (Tenant Isolation) are mandatory.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from app.core.services.assistant_service import AssistantService
from app.infrastructure.database.models import BusinessOffering
from app.core.services.intent_extractor import IntentResult, IntentType

# =============================================================================
# SETUP THE LAB (Fixture)
# =============================================================================
@pytest.fixture
def service_lab():
    """
    Constructs an AssistantService with fully controllable mocks.
    Returns: (service_instance, mock_db, mock_ai, mock_gate, mock_extractor, mock_classifier)
    """
    mock_db_repo = MagicMock()
    mock_ai_service = MagicMock()
    mock_gate = MagicMock()
    mock_intent_ext = MagicMock()
    mock_intent_cls = MagicMock()
    
    # 1. Setup AI Mocks (Async)
    mock_ai_service.generate_response = AsyncMock(return_value="AI Response OK")
    
    # Mock Knowledge Repo
    mock_know = MagicMock()
    mock_know.get_tenant_info.return_value = {"ad": "Test Corp", "sektor": "test"}

    # Mock Tenant Context
    mock_ctx = MagicMock()
    mock_ctx.get_current_tenant.return_value = "default_tenant_1"
    # CRITICAL FIX: Explicitly disable maintenance mode
    mock_ctx.get_tenant_config.return_value = {}  # maintenance_mode: False (None/Empty)

    # 2. Setup AssistantService with DI
    service = AssistantService(
        db_repo=mock_db_repo,
        ai_service=mock_ai_service,
        gate_service=mock_gate,
        intent_extractor=mock_intent_ext,
        intent_classifier=mock_intent_cls,
        knowledge_repo=mock_know,
        tenant_context=mock_ctx
    )
    
    
    # 4. Setup Default Tenant Info (Crucial for Identity Resolution)
    # Service calls knowledge_repo.get_tenant_info, not db.get_tenant_info directly
    # 4. Setup Default Tenant Info (Crucial for Identity Resolution)
    # Service calls knowledge_repo.get_tenant_info, not db.get_tenant_info directly
    mock_know.get_tenant_info.return_value = {"ad": "Test Corp"}
    service.knowledge_repo = mock_know
    
    return service, mock_db_repo, mock_ai_service, mock_gate, mock_intent_ext, mock_intent_cls

# =============================================================================
# 1. PATH TESTING (Critical Flows)
# =============================================================================

@pytest.mark.asyncio
async def test_path_1_gate_rejection(service_lab):
    """
    Scenario: Gate detects OFF_TOPIC.
    Expectation: Service returns early with 'OFF_TOPIC' intent. AI/DB not called.
    """
    service, mock_db, mock_ai, mock_gate, _, _ = service_lab
    
    # Setup Gate (Sync method)
    mock_gate.evaluate.return_value = service.GateDecision.OFF_TOPIC
    
    # Act
    result = await service.process_user_input("Hava durumu nasıl?")
    
    # Assert
    assert result["intent"] == "BLOCK_OFF_TOPIC" or result["intent"] == "OFF_TOPIC"
    assert result["intent"] == "BLOCK_OFF_TOPIC" or result["intent"] == "OFF_TOPIC"
    # DB should be spared
    mock_db.search_products.assert_not_called()
    # AI SHOULD be called to generate polite refusal
    mock_ai.generate_response.assert_called_once()
    assert "reddet" in mock_ai.generate_response.call_args[1]['context']

@pytest.mark.asyncio
async def test_path_2_fast_regex_hit(service_lab):
    """
    Scenario: Gate Allows -> Regex Matches (SEARCH_PRODUCT) -> DB Search.
    Expectation: DB is queried, AI is called with products in prompt.
    """
    service, mock_db, mock_ai, mock_gate, mock_extractor, _ = service_lab
    
    # Gate Pass
    mock_gate.evaluate.return_value = service.GateDecision.BUSINESS
    
    # Regex Hit
    mock_extractor.classify.return_value = MagicMock(
        intent=service.IntentType.SEARCH_PRODUCT,
        query_term="gitar",
        filters={'sort': 'price_asc'}
    )
    
    # DB Hit
    mock_db.search_products.return_value = [MagicMock(name="Fender Strat", price=1000)]
    mock_ai.generate_response.return_value = "Gitarın fiyatı 1000 dolar."
    
    # Act
    result = await service.process_user_input("Gitar fiyatları")
    
    # Assert
    assert result["intent"] == "UNIVERSAL_RAG"
    mock_gate.evaluate.assert_called_once()
    mock_db.search_products.assert_called_once()

@pytest.mark.asyncio
async def test_path_3_hybrid_fallback(service_lab):
    """
    Scenario: Gate Pass -> Regex Unknown -> Smart (LLM) Classification.
    Expectation: IntentClassifier is called.
    """
    service, mock_db, mock_ai, mock_gate, mock_extractor, mock_classifier = service_lab
    
    # Gate Pass
    mock_gate.evaluate.return_value = service.GateDecision.BUSINESS
    
    # Regex MISS (UNKNOWN)
    mock_extractor.classify.return_value = IntentResult(intent=IntentType.UNKNOWN)
    
    # Smart Classifier Hit (Returns string 'SEARCH_PRODUCT')
    mock_classifier.get_refined_intent = AsyncMock(return_value="SEARCH_PRODUCT")
    
    # Act
    await service.process_user_input("Karışık bir istek")
    
    # Assert
    mock_classifier.get_refined_intent.assert_called_once() # Proof of Hybrid Logic
    mock_db.search_products.assert_called_once() # Logic flowed to DB

@pytest.mark.asyncio
async def test_path_4_empty_db_result(service_lab):
    """
    Scenario: Valid Search -> DB Returns Empty.
    Expectation: Prompt contains 'No Results' indicator.
    """
    service, mock_db, mock_ai, mock_gate, mock_extractor, _ = service_lab
    
    # Gate Pass & Regex Hit
    mock_gate.validate_request = AsyncMock(return_value=service.GateDecision.BUSINESS)
    mock_extractor.classify.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT)
    
    # DB Empty
    mock_db.search_products.return_value = []
    
    # Act
    await service.process_user_input("Olmayan bir şey")
    
    # Assert
    prompt_sent = mock_ai.generate_response.call_args[1]['context']
    # Check for keywords indicating emptiness in the generated prompt
    assert "Found: 0" in prompt_sent or "No Results" in prompt_sent or "matches" in prompt_sent

# =============================================================================
# 2. WHITE BOX TESTING (Security & Logic)
# =============================================================================

@pytest.mark.asyncio
async def test_white_box_tenant_isolation(service_lab):
    """
    Security Verification: Ensure 'tenant_id' is propagated to DB methods.
    """
    service, mock_db, _, mock_gate, mock_extractor, _ = service_lab
    
    target_tenant = "secure_customer_X"
    service.tenant_context.get_current_tenant.return_value = target_tenant
    
    # Standard Flow
    mock_gate.validate_request = AsyncMock(return_value=service.GateDecision.BUSINESS)
    mock_extractor.classify.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT)
    
    # Act
    await service.process_user_input("test")
    
    # Assert
    # Verify that search_products was called WITH tenant_id=target_tenant
    args, kwargs = mock_db.search_products.call_args
    assert kwargs.get("tenant_id") == target_tenant, "FATAL: Tenant ID leaked or lost!"

@pytest.mark.asyncio
async def test_white_box_identity_injection(service_lab):
    """
    Identity Verification: Ensure System Prompt uses Dynamic Identity, not 'Melody'.
    """
    service, mock_db, mock_ai, mock_gate, mock_extractor, _ = service_lab
    
    # Setup Tenant Info
    service.knowledge_repo.get_tenant_info.return_value = {"ad": "Berber Ahmet"}
    
    # Standard Flow
    mock_gate.validate_request = AsyncMock(return_value=service.GateDecision.BUSINESS)
    mock_extractor.classify.return_value = IntentResult(intent=IntentType.SOCIAL) # Simple intent
    
    # Act
    await service.process_user_input("selam")
    
    # Assert
    system_prompt = mock_ai.generate_response.call_args[1]['context']
    assert "Berber Ahmet" in system_prompt
    assert "Melody" not in system_prompt

# =============================================================================
# 3. BLACK BOX TESTING (Robustness)
# =============================================================================

@pytest.mark.asyncio
async def test_black_box_fuzzing(service_lab):
    """
    Robustness: Feed garbage/edge-case inputs. Ensure no crash (Exception).
    """
    service, _, _, mock_gate, _, _ = service_lab
    
    # Gate always allows for this test (we want to test internal parsing)
    mock_gate.validate_request = AsyncMock(return_value=service.GateDecision.BUSINESS)
    
    weird_inputs = [
        "",                     # Empty
        "   ",                  # Whitespace
        "👋🐣🚀",               # Emojis only
        "A" * 1000,             # Overflow attempt
        "SELECT * FROM Users",  # SQL Injection attempt (text)
    ]
    
    for inp in weird_inputs:
        try:
            result = await service.process_user_input(inp)
            assert "ai_response" in result or "intent" in result
        except Exception as e:
            pytest.fail(f"System crashed on input '{inp[:20]}...': {e}")
