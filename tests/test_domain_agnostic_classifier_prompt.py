"""
Test Domain Agnostic Classifier Prompt
======================================
Verifies that the IntentClassifier uses the correct, domain-agnostic system prompt
by inspecting the call to the newly implemented 'classify_text' method.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.services.intent_classifier import IntentClassifier

@pytest.mark.asyncio
async def test_classifier_uses_agnostic_prompt():
    """
    Ensure the system prompt sent to `classify_text` contains generic service examples
    (e.g., 'Saç kesimi') and NOT music-specific bias (e.g., 'Metallica').
    """
    # Setup Mock AI
    mock_ai = AsyncMock()
    mock_ai.classify_text.return_value = "DOMAIN"
    
    classifier = IntentClassifier(ai_service=mock_ai)
    
    # Act
    await classifier.classify("test query")
    
    # Assert
    mock_ai.classify_text.assert_called_once()
    call_args = mock_ai.classify_text.call_args
    _, kwargs = call_args
    
    # Check arguments (kwargs might be empty if positional args used, let's check both)
    # The signature is classify_text(system_prompt, user_text)
    # The call was: await self.ai.classify_text(system_prompt=system_prompt, user_text=user_prompt)
    
    system_prompt = kwargs.get('system_prompt')
    if not system_prompt:
        # Fallback to positional args if any
        if call_args[0]:
            system_prompt = call_args[0][0]
            
    assert system_prompt is not None, "System prompt was not passed to classify_text"
    
    # Validation: Check for generic terms and absence of specific music terms
    assert "Saç kesimi fiyatı" in system_prompt
    assert "Hangi hizmetler var?" in system_prompt
    assert "Metallica" not in system_prompt
    assert "Ne tür müzikler var?" not in system_prompt
    
    print("\nSUCCESS: System prompt is domain-agnostic and clean.")

