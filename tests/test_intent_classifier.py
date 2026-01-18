"""
Test suite for Semantic Intent Classifier
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.core.services.intent_classifier import IntentClassifier


@pytest.fixture
def classifier():
    ai_service = AsyncMock()
    # Default to DOMAIN
    ai_service.classify_text.return_value = "DOMAIN"
    return IntentClassifier(ai_service)


@pytest.mark.asyncio
async def test_conversation_intent(classifier):
    """Test that greetings and small talk are classified as CONVERSATION"""
    classifier.ai.classify_text.return_value = "CONVERSATION"
    assert await classifier.classify("Naber moruk") == "CONVERSATION"
    assert await classifier.classify("Merhaba") == "CONVERSATION"


@pytest.mark.asyncio
async def test_meta_intent(classifier):
    """Test that system checks are classified as META"""
    classifier.ai.classify_text.return_value = "META"
    assert await classifier.classify("Sesim geliyor mu?") == "META"
    assert await classifier.classify("Hi, are you there?") == "META"


@pytest.mark.asyncio
async def test_domain_intent(classifier):
    """Test that product queries are classified as DOMAIN"""
    classifier.ai.classify_text.return_value = "DOMAIN"
    assert await classifier.classify("Metallica songs") == "DOMAIN"
    assert await classifier.classify("Ne tür müzikler var?") == "DOMAIN"


@pytest.mark.asyncio
async def test_off_topic_intent(classifier):
    """Test that irrelevant topics are classified as OFF_TOPIC"""
    classifier.ai.classify_text.return_value = "OFF_TOPIC"
    assert await classifier.classify("What's your favorite color?") == "OFF_TOPIC"


@pytest.mark.asyncio
async def test_empty_input(classifier):
    """Test that empty input is classified as OFF_TOPIC"""
    assert await classifier.classify("") == "OFF_TOPIC"
    assert await classifier.classify("   ") == "OFF_TOPIC"


@pytest.mark.asyncio
async def test_fallback_on_error(classifier):
    """Test that classifier falls back to DOMAIN on error"""
    classifier.ai.classify_text.side_effect = Exception("API Error")
    # Should fallback to DOMAIN
    assert await classifier.classify("test query") == "DOMAIN"

@pytest.mark.asyncio
async def test_invalid_response_handling(classifier):
    """Test that classifier handles invalid LLM responses"""
    classifier.ai.classify_text.return_value = "INVALID_RESPONSE"
    # Should fallback to DOMAIN if response is weird
    assert await classifier.classify("test query") == "DOMAIN"
