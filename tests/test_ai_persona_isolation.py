# -*- coding: utf-8 -*-
"""
AI Persona Isolation Test (TDD RED Phase)
=========================================
Ensures that the AI persona is derived ONLY from the runtime context,
not from any hardcoded global configuration.

This is a critical SaaS requirement:
Tenant A must never see Tenant B's identity (e.g., Chinook).
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.infrastructure.ai.groq_service import GroqAIService

# Mock configuration to ensure we don't accidentally hit real APIs during persona test
# We want to test prompt construction logic primarily, but since GroqAIService 
# sends request to API, we might need to mock the API call OR inspect the constructed prompt.
# Since _get_system_prompt is internal (protected), testing it directly is a bit grey-box but essential here.

class TestAIPersonaIsolation:
    
    def test_system_prompt_is_tenant_agnostic_by_default(self):
        """
        CRITICAL TEST: The system prompt construction MUST BE GENERIC.
        It should NOT contain hardcoded references, nor depend on context injection 
        into the system prompt itself context is injected into user message).
        """
        # Arrange
        service = GroqAIService("fake_key")
        
        # Act
        otel_context = "ŞİRKET BİLGİSİ (VİZYON): Vizyonumuz otelcilikte bir numara olmak."
        prompt_otel = service._get_system_prompt(context=otel_context)
        
        # Assert - SAAS VALIDATION
        
        # 1. Prompt should be GENERIC (Stateless)
        assert "Sen yardımcı bir sesli asistansın" in prompt_otel
        
        # 2. Prompt SHOULD NOT contain specific company names by default
        assert "Chinook" not in prompt_otel, "Hardcoded 'Chinook' found in prompt!"
        
        # 3. Context is NOT injected into System Prompt (it goes to User Message in this arch)
        # So we assert that system prompt is CLEAN
        assert "otelcilikte bir numara" not in prompt_otel

    @pytest.mark.asyncio
    async def test_ai_response_reflects_context_identity(self):
        """
        Verifies that the AI receives the context properly in the message history.
        """
        # Arrange
        service = GroqAIService("fake_key")
        service.client = AsyncMock()
        service.client.chat.completions.create = AsyncMock(return_value=MagicMock())
        
        # Act
        context_data = "ŞİRKET KİMLİĞİ: Otel İstanbul. Biz bir oteliz."
        await service.generate_response("Vizyonunuz nedir?", context=context_data)
        
        # Assert
        call_args = service.client.chat.completions.create.call_args
        assert call_args is not None
        
        messages = call_args.kwargs['messages']
        
        # Check if context is present in ANY message (likely USER role)
        full_conversation = "\n".join([m['content'] for m in messages])
        
        assert "Otel İstanbul" in full_conversation, "Context was not sent to LLM!"
        assert "Chinook" not in full_conversation, "Hardcoded 'Chinook' leaked into conversation!"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
