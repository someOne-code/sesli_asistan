
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.services.assistant_service import AssistantService
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
from app.core.services.intent_extractor import IntentResult, IntentType

@pytest.mark.asyncio
async def test_demo_scenario_berber_ahmet():
    """
    DEMO SENARYOSU - BERBER AHMET
    Müşteri: "Saç kesimi ne kadar?"
    Beklenen: 
    1. Sistem Berber Ahmet olduğunu bilecek.
    2. Listeden 'Saç Kesimi' fiyatını bulacak (100 TL).
    3. AI, berber kimliğiyle kısa ve net cevap verecek.
    """
    # 1. ORTAMI KUR (Mocking)
    mock_db = MagicMock()
    mock_ai = AsyncMock()
    mock_normalizer = MagicMock()
    mock_normalizer.normalize.side_effect = lambda x: x.lower() # Basit normalize
    
    # AI Simülasyonu (LLM cevabı)
    mock_ai.generate_response.return_value = "Saç kesimi ücretimiz 100 Türk Lirasıdır efendim."
    
    # DB Simülasyonu (Ürünler)
    mock_product = MagicMock()
    mock_product.name = "Saç Kesimi"
    mock_product.price = 100.0
    mock_product.currency = "TRY"
    mock_product.description = "Modern Kesim"
    
    mock_db.search_products.return_value = [mock_product]
    mock_db.get_tenant_info.return_value = {"ad": "Berber Ahmet"}

    # 2. SERVİSİ BAŞLAT
    ctx = StaticTenantContext("berber_ahmet")
    service = AssistantService(mock_db, mock_ai, mock_normalizer, tenant_context=ctx)
    
    # 3. KONUŞMA BAŞLASIN
    print("\n\n📞 [Müşteri]: 'Saç kesimi ne kadar?'")
    
    # Intent'i manuel set ediyoruz (Regex'in doğru çalıştığını varsayıyoruz demo için garanti olsun)
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as mock_classify:
        mock_classify.return_value = IntentResult(
            intent=IntentType.SEARCH_PRODUCT,
            query_term="saç kesimi"
        )
        
        response = await service.process_user_input("Saç kesimi ne kadar?")
    
    # 4. SONUÇLARI İNCELE
    print(f"🤖 [Asistan]: '{response['ai_response']}'")
    
    # Kontroller
    print(f"DB Call Args: {mock_db.search_products.call_args}")
    assert mock_db.search_products.called, "DB search_products metodu hiç çağrılmadı!"
    # Check for the query term passed to the method
    assert "saç kesimi" in str(mock_db.search_products.call_args), "DB'de yanlış terim arandı!"
    ai_context = mock_ai.generate_response.call_args.kwargs['context']
    
    print("\n🔍 [Sistem Aklı / Context]:")
    print("-" * 30)
    print(ai_context)
    print("-" * 30)
    
    assert "Berber Ahmet" in ai_context, "HATA: Asistan kimliğini unutmuş!"
    assert "100.0" in ai_context, "HATA: Fiyat bilgisi AI'ya gitmemiş!"
    
    print("\n✅ DEMO TESTİ BAŞARILI: Müşteri fiyatı aldı, asistan kimliğini korudu.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_demo_scenario_berber_ahmet())
