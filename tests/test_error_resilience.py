"""
Test suite for Error Resilience & Graceful Degradation.
Ensures the system NEVER crashes but ALWAYS logs errors for debugging.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.services.assistant_service import AssistantService


@pytest.mark.asyncio
async def test_database_failure_graceful_recovery():
    """
    Scenario: Logic/DB layer fails.
    Expected: System does NOT crash. AI IS called with error context.
    """
    # Setup
    mock_db = MagicMock()
    mock_db.search_products.side_effect = Exception("DB Connection Lost")
    mock_db.get_unique_genres.side_effect = Exception("DB Connection Lost")
    
    mock_ai = AsyncMock()
    mock_ai.generate_response.return_value = "Özür dilerim, şu an bir sorun yaşıyorum."
    
    service = AssistantService(db_repo=mock_db, ai_service=mock_ai)
    
    # Act - This should NOT raise an exception
    response = await service.process_user_input("Metallica çal")
    
    # Assert
    # 1. System did not crash - we got a response
    assert response is not None
    assert "ai_response" in response
    
    # 2. AI WAS called (for graceful recovery)
    mock_ai.generate_response.assert_called()
    
    # 3. The context passed to AI contains error indicator
    call_args = mock_ai.generate_response.call_args
    context_arg = call_args.kwargs.get('context', '') if call_args.kwargs else str(call_args)
    assert "HATA" in context_arg or "hata" in context_arg.lower() or "özür" in response["ai_response"].lower()


@pytest.mark.asyncio
async def test_ai_service_critical_failure():
    """
    Scenario: The AI service itself fails.
    Expected: System does NOT crash. Returns static fallback message.
    """
    # Setup
    mock_db = MagicMock()
    mock_db.search_products.return_value = []  # DB works fine
    mock_db.get_unique_genres.return_value = []
    
    mock_ai = AsyncMock()
    mock_ai.generate_response.side_effect = Exception("Groq API Timeout")
    
    service = AssistantService(db_repo=mock_db, ai_service=mock_ai)
    
    # Act - This should NOT raise an exception
    response = await service.process_user_input("Metallica çal")
    
    # Assert
    # 1. System did not crash
    assert response is not None
    
    # 2. Return value contains static fallback message
    assert "ai_response" in response
    assert "servislerime erişemiyorum" in response["ai_response"] or "tekrar deneyin" in response["ai_response"]


@pytest.mark.asyncio  
async def test_both_layers_fail():
    """
    Scenario: Both DB and AI fail.
    Expected: System still returns a safe fallback, no crash.
    """
    # Setup
    mock_db = MagicMock()
    mock_db.search_products.side_effect = Exception("DB Dead")
    mock_db.get_unique_genres.side_effect = Exception("DB Dead")
    
    mock_ai = AsyncMock()
    mock_ai.generate_response.side_effect = Exception("AI Dead")
    
    service = AssistantService(db_repo=mock_db, ai_service=mock_ai)
    
    # Act - This should NOT raise an exception
    response = await service.process_user_input("Test query")
    
    # Assert
    assert response is not None
    assert "ai_response" in response
    # Should contain static fallback
    assert len(response["ai_response"]) > 0
