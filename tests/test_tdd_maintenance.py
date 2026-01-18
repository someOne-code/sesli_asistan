
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.core.services.assistant_service import AssistantService

@pytest.mark.asyncio
async def test_maintenance_mode_enforcement():
    """
    TDD CYCLE: RED STAGE (Test Fails First)
    
    Feature: Tenant Maintenance Mode
    Scenario: A tenant is flagged as 'under maintenance'.
    Expected Behavior: The system should immediately return a maintenance message 
                       WITHOUT calling the DB or AI service.
    """
    # 1. SETUP: Dependencies
    mock_db = MagicMock()
    mock_ai = AsyncMock()
    mock_gate = MagicMock()
    mock_ext = MagicMock()
    mock_cls = MagicMock()
    mock_know = MagicMock()
    mock_ctx = MagicMock()
    
    # Configure Tenant as "Under Maintenance"
    mock_ctx.get_current_tenant.return_value = "broken_tenant"
    # Varsayılan olarak böyle bir özellik henüz yok, biz 'varmış gibi' test ediyoruz.
    mock_ctx.get_tenant_config.return_value = {"maintenance_mode": True} 
    
    service = AssistantService(
        db_repo=mock_db, ai_service=mock_ai,
        gate_service=mock_gate, intent_extractor=mock_ext,
        intent_classifier=mock_cls, knowledge_repo=mock_know,
        tenant_context=mock_ctx
    )
    
    # 2. ACT
    # Kullanıcı istek gönderir
    result = await service.process_user_input("Merhaba, ürünlere bakacaktım")
    
    # 3. ASSERT
    # Beklenti 1: Yanıt 'bakım' veya 'maintenance' içermeli
    response_text = result.get("ai_response", "").lower()
    assert "bakım" in response_text or "maintenance" in response_text, \
        f"Expected maintenance message, got: {response_text}"
        
    # Beklenti 2: Veritabanına hiç gidilmemeli (Tasarruf)
    mock_db.search_products.assert_not_called()
    
    # Beklenti 3: AI çağırma maliyeti oluşmamalı (Tasarruf)
    mock_ai.generate_response.assert_not_called()
