
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.services.assistant_service import AssistantService
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
from app.core.services.intent_extractor import IntentResult, IntentType
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository
from app.core.config import settings
from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer

# LIVE INTEGRATION TEST - CHINOOK EXPLORER
# Senaryo: Müşteri ne istediğini tam bilmeden mağazayı geziyor.

async def test_live_chinook_explorer():
    print("\n" + "="*80)
    print("🎧  CANLI SENARYO: MÜZİK KEŞFİ (CHINOOK STORE)")
    print("="*80)
    
    # --- ALTYAPI KURULUMU ---
    db_name = settings.DB_NAME
    real_db_repo = HedefRepository(db_name)
    real_knowledge_repo = SqlKnowledgeRepository(db_name)
    real_normalizer = RuleBasedNormalizer()
    
    # AI Simülasyonu (Context verisi kritiktir)
    mock_ai = AsyncMock()
    mock_ai.generate_response.return_value = "AI: [Cevap Oluşturuldu]"

    ctx = StaticTenantContext("chinook")
    service = AssistantService(
        db_repo=real_db_repo, 
        ai_service=mock_ai, 
        normalizer=real_normalizer, 
        knowledge_repo=real_knowledge_repo,
        tenant_context=ctx
    )

    # -------------------------------------------------------------
    # 1. GENEL BAKIŞ: "Ne tür müzikleriniz var?"
    # -------------------------------------------------------------
    q1 = "Ne tür müzikleriniz var?"
    print(f"\n🗣️  MÜŞTERİ: \"{q1}\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.LIST_CATALOG)
        await service.process_user_input(q1)
        
        ctx_data = mock_ai.generate_response.call_args.kwargs.get('context', '')
        # Chinook'ta çok fazla tür var, en azından birkaçını görelim
        genres = ["Rock", "Jazz", "Metal", "Latin", "Blues"]
        found = [g for g in genres if g in ctx_data]
        
        if len(found) > 2:
            print(f"✅ ASİSTAN: Elimizde şu türler var: {', '.join(found)}...")
        else:
            print("❌ HATA: Türler listelenemedi.")

    # -------------------------------------------------------------
    # 2. ÖZEL TÜR SORGUSU: "Rock parçalar var mı?"
    # -------------------------------------------------------------
    q2 = "Rock parçalar var mı elinizde?"
    print(f"\n🗣️  MÜŞTERİ: \"{q2}\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        # IntentExtractor normalde "rock"ı yakalar, biz simüle ediyoruz
        m_cls.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="rock")
        await service.process_user_input(q2)
        
        ctx_data = mock_ai.generate_response.call_args.kwargs.get('context', '')
        
        if "Rock" in ctx_data and "USD" in ctx_data:
            # Örnek bir rock şarkısı çekelim
            import re
            match = re.search(r"(.*?) \| .*? Rock", ctx_data)
            song = match.group(1).strip() if match else "Birçok Rock parçası"
            print(f"✅ ASİSTAN: Evet, örneğin '{song}' gibi birçok Rock parçamız mevcut.")
        else:
            print("❌ HATA: Rock müzik bulunamadı.")

    # -------------------------------------------------------------
    # 3. SPESİFİK FİYAT SORGUSU: "Fiyatlar nasıl genel olarak?"
    # -------------------------------------------------------------
    # Bu aslında INFORMATIONAL bir soru ama genelde ürün aramaya düşebilir.
    # Biz bunu "GENEL ÜRÜN FİYATI" gibi test edelim.
    q3 = "Fiyatlar ne civarda?"
    print(f"\n🗣️  MÜŞTERİ: \"{q3}\"")
    
    # Asistanın veritabanından rastgele veya popüler ürün çekip fiyat örneği vermesi beklenir
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        # Liste catalog intenti ile fiyat özeti de gidebilir
        m_cls.return_value = IntentResult(intent=IntentType.LIST_CATALOG)
        await service.process_user_input(q3)
        
        ctx_data = mock_ai.generate_response.call_args.kwargs.get('context', '')
        # Context içinde 0.99 veya 1.99 gibi fiyatlar var mı?
        if "0.99" in ctx_data or "1.99" in ctx_data:
             print("✅ ASİSTAN: Şarkılarımız genellikle 0.99 USD, albümler daha yüksek olabilir.")
        else:
             print("❌ HATA: Fiyat bilgisine erişilemedi.")

    # -------------------------------------------------------------
    # 4. KARIŞIK SORGUSU: "Böyle metal, sert bir şeyler lazım."
    # -------------------------------------------------------------
    q4 = "Böyle metal, sert bir şeyler lazım."
    print(f"\n🗣️  MÜŞTERİ: \"{q4}\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="metal")
        await service.process_user_input(q4)
        
        ctx_data = mock_ai.generate_response.call_args.kwargs.get('context', '')
        
        if "Iron Maiden" in ctx_data or "Metallica" in ctx_data or "Metal" in ctx_data:
             print("✅ ASİSTAN: Tabii, Iron Maiden ve Metallica gibi efsaneler arşivimizde.")
        else:
             print("❌ HATA: Metal müzik bulunamadı.")

    print("\n" + "="*80)
    print("MÜZİK KEŞİF TESTİ TAMAMLANDI.")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_live_chinook_explorer())
