import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.services.assistant_service import AssistantService

@pytest.mark.asyncio
async def test_memory_recall():
    """
    Test that the AI receives conversation history in subsequent turns.
    """
    # Setup
    mock_db = MagicMock()
    mock_db.search_products.return_value = []
    mock_db.list_all_products.return_value = []
    mock_db.get_unique_genres.return_value = []
    mock_ai = AsyncMock()
    mock_ai.generate_response.return_value = "Tamam, adını kaydettim."
    
    service = AssistantService(db_repo=mock_db, ai_service=mock_ai)
    
    # Session State (simulated client-side or server-side memory)
    history = []
    
    # Turn 1: "Adım Umut"
    user_input_1 = "Benim adım Umut"
    result_1 = await service.process_user_input(
        user_input_1, 
        conversation_history="\n".join(history)
    )
    # Simulate adding to history (Controller Logic)
    history.append(f"User: {user_input_1}")
    history.append(f"AI: {result_1['ai_response']}")
    
    # Turn 2: "Adım ne?"
    user_input_2 = "Adım ne?"
    # Mock AI response based on history presence
    def side_effect(*args, **kwargs):
        hist = kwargs.get('conversation_history', '')
        if "Umut" in hist:
            return "Senin adın Umut."
        return "Adını bilmiyorum."
        
    mock_ai.generate_response.side_effect = side_effect
    
    result_2 = await service.process_user_input(
        user_input_2,
        conversation_history="\n".join(history)
    )
    
    # Assert
    assert "Umut" in result_2['ai_response']
    # Verify AI service was called with history containing "Umut"
    call_args = mock_ai.generate_response.call_args
    _, kwargs = call_args
    assert "User: Benim adım Umut" in kwargs['conversation_history']
