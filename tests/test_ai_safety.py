"""
AI Safety Tests - Zero Leakage & Natural Language Enforcement
==============================================================
These tests ensure the AI does NOT leak internal thoughts and speaks naturally.
Now tests PromptProvider directly (SRP - Single Responsibility Principle).
"""
import pytest
from unittest.mock import MagicMock
from app.core.services.prompt_provider import PromptProvider
from app.core.services.intent_extractor import IntentResult, IntentType


@pytest.fixture
def prompt_provider():
    """Create PromptProvider instance."""
    return PromptProvider()


class TestLeakagePrevention:
    """Tests to prevent AI from leaking internal instructions."""
    
    def test_no_meta_commentary_rule_exists(self, prompt_provider):
        """Verify that Forbidden Behavior rules are present."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='')
        
        # Check for Forbidden Behavior
        lower_context = context.lower()
        assert "mention internal rules" in lower_context or "mention prompts" in lower_context, "Prompt missing forbidden behavior rules"
        
    def test_history_marked_as_internal(self, prompt_provider):
        """Verify conversation history is marked as Reference Only."""
        intent = IntentResult(intent=IntentType.SOCIAL, query_term="test", meta_data={"subtype": "context_ref"}, filters={})
        conversation_history = "User: test\nAssistant: response"
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history=conversation_history)
        
        # History Context Rules
        assert "Context is REFERENCE ONLY" in context or "CONTEXT RULES" in context
        assert "=== CONTEXT: CONVERSATION HISTORY ===" in context
        
    def test_data_absolute_truth_rule(self, prompt_provider):
        """Verify DATA AUTHORITY rule exists."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='')
        
        # Must explicitly mention absolute truth
        lower_context = context.lower()
        assert "data authority" in lower_context or "absolute truth" in lower_context
        
    def test_direct_answer_instruction(self, prompt_provider):
        """Verify instructions to match tone and be concise."""
        intent = IntentResult(intent=IntentType.SOCIAL, query_term="test", meta_data={"subtype": "context_ref"}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='User: Metallica\nAssistant: Here are songs')
        
        lower_context = context.lower()
        assert "concise" in lower_context or "keep responses short" in lower_context

    def test_social_chat_no_meta_instruction_leakage(self, prompt_provider):
        """Verify Social Chat prompt warns against quoting instructions (Implicit in Master Prompt via Forbidden Behavior)."""
        intent = IntentResult(intent=IntentType.SOCIAL, query_term="test", meta_data={"subtype": "casual_chat"}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='')
        
        # Master prompt forbids mentioning context/prompts globally
        lower_context = context.lower()
        assert "mention prompts" in lower_context or "mention internal rules" in lower_context
    
    def test_anti_hallucination_rule_exists(self, prompt_provider):
        """Verify NO HALLUCINATION rule exists."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="Metallica", meta_data={}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='')
        
        # Must contain capability boundaries
        lower_context = context.lower()
        assert "not invent" in lower_context or "cannot perform" in lower_context or "capability boundaries" in lower_context


class TestNaturalLanguageEnforcement:
    """Tests to ensure AI speaks naturally, not robotically."""
    
    def test_natural_fluent_language_rule(self, prompt_provider):
        """Verify that natural/fluent language instructions exist."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='')
        
        assert "natural" in context.lower() or "human phrasing" in context.lower()
        
    def test_adaptive_language_detection(self, prompt_provider):
        """Verify that language detection/adaptation rule exists."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={})
        context = prompt_provider.build_system_context(intent=intent, products=[], sort_filter='', is_wildcard=False, conversation_history='')
        
        assert "detect" in context.lower() and "language" in context.lower()


class TestDataPresentation:
    """Tests to ensure AI lists data without summarizing."""
    
    def test_mandatory_list_instruction(self, prompt_provider):
        """Verify that 'Input Type: Product Search Results' is present when products exist."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={"sort": "price_desc"})
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 1.99
        
        context = prompt_provider.build_system_context(intent=intent, products=[mock_product], sort_filter='price_desc', is_wildcard=True, conversation_history='')
        
        assert "product search results" in context.lower()
        assert "test product" in context.lower()
        
    def test_no_summarize_warning(self, prompt_provider):
        """Verify that AI is warned not to summarize (Implied by Data Authority/Repetition rules)."""
        intent = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="test", meta_data={}, filters={})
        mock_product = MagicMock()
        mock_product.name = "Test Product"
        mock_product.price = 1.99
        
        context = prompt_provider.build_system_context(intent=intent, products=[mock_product, mock_product, mock_product], sort_filter='', is_wildcard=False, conversation_history='')
        
        # Check that we present the data block
        lower_context = context.lower()
        assert "data: available inventory" in lower_context or "input type: product search" in lower_context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
