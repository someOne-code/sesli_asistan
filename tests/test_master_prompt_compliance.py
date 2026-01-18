"""
Master Prompt Compliance Tests
==============================
Guarantees that the AI Constitution (MASTER PROMPT) is strictly enforced.
Prevents:
1. Domain Leakage (e.g. suggesting guitars in a barber shop context)
2. Hallucination (e.g. promising to 'play' music or 'take orders')
3. Generic Fallbacks (e.g. music/food/travel examples)
"""
import pytest
from unittest.mock import MagicMock
from app.core.services.prompt_provider import PromptProvider
from app.core.services.intent_extractor import IntentResult, IntentType

@pytest.fixture
def prompt_provider():
    return PromptProvider()

def test_tenant_identity_injection(prompt_provider):
    """Verify that the AI represents the SPECIFIC tenant injected, and no other."""
    tenant_info = {"ad": "Berber Ahmet Efendi"}
    intent = IntentResult(intent=IntentType.SOCIAL, query_term="selam", meta_data={}, filters={})
    
    context = prompt_provider.build_system_context(
        intent=intent,
        products=[],
        tenant_info=tenant_info
    )
    
    assert "Your tenant identity is: Berber Ahmet Efendi" in context
    # Assert AI should identify as the tenant, not the legacy 'Melody'
    assert "Berber Ahmet" in context and "Melody" not in context

def test_capability_boundaries_enforced(prompt_provider):
    """Verify that playing, booking, and ordering are explicitly forbidden."""
    intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="Metallica", meta_data={}, filters={})
    
    context = prompt_provider.build_system_context(intent=intent, products=[])
    
    # Check for strict capability limits
    lower_context = context.lower()
    assert "cannot:" in lower_context
    assert "play" in lower_context
    assert "order" in lower_context
    assert "book" in lower_context
    assert "information-only" in lower_context

def test_no_generic_fallbacks_rule(prompt_provider):
    """Verify that generic examples (music, food, travel) are FORBIDDEN fallbacks."""
    intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="olmayan_ürün", meta_data={}, filters={})
    
    context = prompt_provider.build_system_context(intent=intent, products=[])
    
    # The rule must exist in the prompt
    assert "Fall back to generic examples (e.g. music, food, travel)" in context
    assert "You MUST NOT:" in context
    
    # Ensure task context for empty results doesn't suggest guitars
    task_context = context.split("TASK CONTEXT:")[1]
    assert "gitar" not in task_context.lower()
    assert "metallica" not in task_context.lower()
    assert "apologize" in task_context.lower()

def test_data_authority_is_absolute(prompt_provider):
    """Verify that the provided context is the only source of truth."""
    intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={})
    
    context = prompt_provider.build_system_context(intent=intent, products=[])
    
    assert "DATA AUTHORITY" in context
    assert "absolute truth" in context.lower()
    assert "Do NOT invent alternatives" in context

def test_stateless_mental_model_exists(prompt_provider):
    """Verify the AI mental model is set to stateless interface, not 'chatbot'."""
    intent = IntentResult(intent=IntentType.SOCIAL, query_term="hi", meta_data={}, filters={})
    
    context = prompt_provider.build_system_context(intent=intent, products=[])
    
    assert "MENTAL MODEL" in context
    assert "You are not a chatbot" in context
    assert "stateless language model" in context.lower()

def test_no_reintroduction_logic(prompt_provider):
    """Verify the prompt forbids re-introducing Melody if history exists."""
    history = "User: Hello\nAssistant: I am Melody, how can I help?"
    intent = IntentResult(intent=IntentType.SOCIAL, query_term="who are you", meta_data={}, filters={})
    
    context = prompt_provider.build_system_context(intent=intent, products=[], conversation_history=history)
    
    assert "Do NOT reintroduce yourself if history exists" in context
    assert "=== CONTEXT: CONVERSATION HISTORY ===" in context
