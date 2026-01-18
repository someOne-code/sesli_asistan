"""
Unit Tests for AI Manager (GroqMiddleware).
Uses Mocks to avoid real API calls.
Updated for Universal Retrieval Architecture.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.infrastructure.ai.groq_service import GroqAIService

@pytest.fixture
def mock_groq_client():
    """Mock the AsyncGroq client completely"""
    with patch("app.infrastructure.ai.groq_service.AsyncGroq") as MockClient:
        client_instance = MockClient.return_value
        # Mock chat.completions.create
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "UNIVERSAL_RETRIEVAL" # Default for intent
        mock_response.choices = [MagicMock(message=mock_message)]
        
        client_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        yield client_instance

@pytest.fixture
def ai_service(mock_groq_client):
    service = GroqAIService(api_key="fake-key")
    # Inject the mock client instance
    service.client = mock_groq_client
    return service

@pytest.mark.asyncio
async def test_determine_intent_universal(ai_service, mock_groq_client):
    """
    Universal Retrieval means intent is always effectively UNIVERSAL_RETRIEVAL
    or handled by the single query pipeline.
    """
    # Act
    intent = await ai_service.determine_intent("Metallica çal")
    
    # Assert
    assert intent == "UNIVERSAL_RETRIEVAL"



@pytest.mark.asyncio
async def test_stream_error_handling(ai_service, mock_groq_client):
    """Should handle stream errors gracefully"""
    # Mock stream to raise exception
    mock_groq_client.chat.completions.create.side_effect = Exception("API Error")
    
    chunks = []
    async for chunk in ai_service.generate_response_stream("Test"):
        chunks.append(chunk)
        
    # The service yields a user-friendly error message on exception
    assert "Bağlantı hatası" in "".join(chunks) or "hata oluştu" in "".join(chunks)
