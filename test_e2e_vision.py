# -*- coding: utf-8 -*-
"""
End-to-End Test: Company Vision Query
======================================
Tests the complete flow from user input to knowledge retrieval.
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.services.assistant_service import AssistantService
from app.infrastructure.database.repository import HedefRepository
from unittest.mock import AsyncMock


async def test_vision_query():
    """Test: 'Vizyonunuz nedir?' should return company vision from DB."""
    
    print("=" * 60)
    print("E2E TEST: Company Vision Query")
    print("=" * 60)
    
    # Setup
    db_repo = HedefRepository("hedef.db")
    mock_ai = AsyncMock()
    mock_ai.generate_response = AsyncMock(
        return_value="Vizyonumuz, yapay zeka teknolojilerini her işletmenin ulaşabileceği basitlikte sunmaktır."
    )
    
    service = AssistantService(db_repo=db_repo, ai_service=mock_ai)
    
    # Act
    print("\n[USER] Vizyonunuz nedir?\n")
    result = await service.process_user_input("Vizyonunuz nedir?", session_id="test_123")
    
    # Assert
    print("\n" + "=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(f"Intent: {result.get('intent')}")
    print(f"AI Response: {result.get('ai_response')}")
    print(f"Context Used: {result.get('context_used', 'N/A')[:200]}...")
    
    # Verify
    assert result.get('intent') == 'INFORMATIONAL', f"Expected INFORMATIONAL, got {result.get('intent')}"
    
    # Check if company vision was fetched from DB
    context = result.get('context_used', '')
    assert 'vizyon' in context.lower() or 'yapay zeka' in context.lower(), \
        "Company vision should be in context"
    
    print("\n✅ TEST PASSED: Vision query correctly routed to knowledge base!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_vision_query())
