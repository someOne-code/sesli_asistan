"""
Test suite for ReflexAgent (Conversational Fillers)
Tests that immediate fillers are triggered for DOMAIN queries to mask latency.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.core.services.reflex_agent import ReflexAgent


@pytest.mark.asyncio
async def test_reflex_agent_returns_filler_for_domain():
    """Test that ReflexAgent returns a filler phrase for DOMAIN intent"""
    agent = ReflexAgent()
    
    filler = await agent.get_filler("DOMAIN")
    
    # Should return a non-empty string
    assert filler is not None
    assert len(filler) > 0
    assert isinstance(filler, str)


@pytest.mark.asyncio
async def test_reflex_agent_no_filler_for_conversation():
    """Test that ReflexAgent does NOT return filler for CONVERSATION intent"""
    agent = ReflexAgent()
    
    filler = await agent.get_filler("CONVERSATION")
    
    # Should return None or empty string
    assert filler is None or filler == ""


@pytest.mark.asyncio
async def test_reflex_agent_no_filler_for_meta():
    """Test that ReflexAgent does NOT return filler for META intent"""
    agent = ReflexAgent()
    
    filler = await agent.get_filler("META")
    
    # Should return None or empty string
    assert filler is None or filler == ""


@pytest.mark.asyncio
async def test_reflex_agent_randomizes_fillers():
    """Test that ReflexAgent randomizes filler phrases"""
    agent = ReflexAgent()
    
    # Get 10 fillers and check if they're not all the same
    fillers = [await agent.get_filler("DOMAIN") for _ in range(10)]
    
    # Should have at least 2 different fillers in 10 tries
    unique_fillers = set(fillers)
    assert len(unique_fillers) >= 2


@pytest.mark.asyncio
async def test_reflex_agent_filler_is_professional():
    """Test that filler phrases are professional and appropriate"""
    agent = ReflexAgent()
    
    filler = await agent.get_filler("DOMAIN")
    
    # Should contain professional Turkish phrases
    professional_keywords = ["bakıyorum", "kontrol", "saniye", "arayalım", "buluyorum"]
    assert any(keyword in filler.lower() for keyword in professional_keywords)


@pytest.mark.asyncio
async def test_reflex_agent_filler_is_short():
    """Test that filler phrases are short (< 50 characters)"""
    agent = ReflexAgent()
    
    filler = await agent.get_filler("DOMAIN")
    
    # Should be concise
    assert len(filler) < 50
