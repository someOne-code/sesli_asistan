# -*- coding: utf-8 -*-
"""
SaaS Acceptance Test - Multi-Tenant Persona & Scope Validation
=============================================================
This test verifies the core SaaS promise: 
Two different businesses (Berber vs Music) can use the same code 
but receive completely isolated and correct personas/data.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.services.assistant_service import AssistantService
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
from app.core.services.conversation_gate import GateDecision
from app.core.services.intent_extractor import IntentResult, IntentType

@pytest.fixture
def saas_setup():
    """Setup a standard service structure with mocked dependencies."""
    mock_db = MagicMock()
    mock_ai = AsyncMock()
    mock_normalizer = MagicMock()
    
    # Default behavior for normalizer
    mock_normalizer.normalize.side_effect = lambda x: x.lower()
    
    return mock_db, mock_ai, mock_normalizer

@pytest.mark.asyncio
async def test_saas_isolation_berber_vs_music(saas_setup):
    """
    Scenario: Verify that the same AssistantService logic serves 
    two different masters correctly without data leakage.
    """
    mock_db, mock_ai, mock_normalizer = saas_setup
    
    # --- TENANT A: BERBER AHMET ---
    berber_ctx = StaticTenantContext("berber_ahmet")
    berber_service = AssistantService(
        db_repo=mock_db, 
        ai_service=mock_ai, 
        normalizer=mock_normalizer,
        tenant_context=berber_ctx
    )
    
    # Mock Data for Berber
    mock_db.get_tenant_info.return_value = {"ad": "Berber Ahmet Efendi", "sektor": "berber"}
    mock_db.get_catalog_summary.return_value = ["Saç Kesim", "Sakal Tıraşı"]
    
    # Act: User asks Berber for services
    # Mock intent to LIST_CATALOG
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as mock_classify:
        mock_classify.return_value = IntentResult(intent=IntentType.LIST_CATALOG)
        await berber_service.process_user_input("Neler yapıyorsun?")
    
    # Assert Berber Context
    berber_call = mock_ai.generate_response.call_args_list[-1]
    berber_prompt = berber_call.kwargs['context']
    
    assert "Berber Ahmet Efendi" in berber_prompt
    assert "Saç Kesim" in berber_prompt
    assert "Chinook" not in berber_prompt, "Leak detected: Music brand found in Berber prompt!"

    # --- TENANT B: CHINOOK MUSIC ---
    music_ctx = StaticTenantContext("chinook_music")
    music_service = AssistantService(
        db_repo=mock_db, 
        ai_service=mock_ai, 
        normalizer=mock_normalizer,
        tenant_context=music_ctx
    )
    
    # Mock Data for Music
    mock_db.get_tenant_info.return_value = {"ad": "Chinook Müzik Mağazası", "sektor": "muzik"}
    mock_db.get_catalog_summary.return_value = ["Rock", "Pop", "Jazz"]
    
    # Act: User asks Music store for services
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as mock_classify:
        mock_classify.return_value = IntentResult(intent=IntentType.LIST_CATALOG)
        await music_service.process_user_input("Hangi türler var?")
    
    # Assert Music Context
    music_call = mock_ai.generate_response.call_args_list[-1]
    music_prompt = music_call.kwargs['context']
    
    assert "Chinook Müzik Mağazası" in music_prompt
    assert "Rock" in music_prompt
    assert "Berber" not in music_prompt, "Leak detected: Barber brand found in Music prompt!"

@pytest.mark.asyncio
async def test_saas_knowledge_isolation(saas_setup):
    """
    Ensures that company-specific knowledge is isolated.
    """
    mock_db, mock_ai, mock_normalizer = saas_setup
    
    # We need to mock the Knowledge Repository specifically
    mock_knowledge_repo = MagicMock()
    
    berber_ctx = StaticTenantContext("berber_ahmet")
    service = AssistantService(
        db_repo=mock_db,
        ai_service=mock_ai,
        knowledge_repo=mock_knowledge_repo,
        tenant_context=berber_ctx
    )
    
    # 1. Berber asking for vision
    mock_knowledge_repo.get.return_value = "Vizyonumuz: Herkesi bıyıklı yapmak."
    mock_db.get_tenant_info.return_value = {"ad": "Berber Ahmet"}
    
    # Mock the intent as INFORMATIONAL to trigger knowledge lookup
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as mock_classify:
        mock_classify.return_value = IntentResult(
            intent=IntentType.INFORMATIONAL, 
            meta_data={"topic": "vizyon"}
        )
        
        await service.process_user_input("Vizyonunuz nedir?")
    
    # Verify Knowledge Repo was called with CORRECT tenant
    args, kwargs = mock_knowledge_repo.get.call_args
    assert kwargs.get("tenant_id") == "berber_ahmet"
    
    # Verify AI prompt contains the barber vision
    final_call = mock_ai.generate_response.call_args_list[-1]
    assert "bıyıklı yapmak" in final_call.kwargs['context']
