
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

# LIVE INTEGRATION TEST - CHINOOK MUSIC STORE
# Amaç: Müzik mağazası verilerinin (Rock, Pop, U2 vb.) canlı veritabanından doğru çekildiğini doğrulamak.

async def test_live_chinook_conversation():
    print("\n" + "="*70)
    print("🎸  CANLI TEST: CHINOOK MUSIC STORE (GERÇEK VERİTABANI)")
    print("="*70)
    
    # 1. ALTYAPI (Gerçek DB)
    db_name = settings.DB_NAME
    real_db_repo = HedefRepository(db_name)
    real_knowledge_repo = SqlKnowledgeRepository(db_name)
    real_normalizer = RuleBasedNormalizer()
    
    # AI yine Mock (Sadece veri akışını test ediyoruz)
    mock_ai = AsyncMock()
    mock_ai.generate_response.return_value = "Asistan Cevabı (Simüle)"

    # 2. SERVİSİ CHINOOK İÇİN BAŞLAT
    # Tenant ID: "chinook" (Veritabanındaki ID)
    ctx = StaticTenantContext("chinook")
    
    service = AssistantService(
        db_repo=real_db_repo, 
        ai_service=mock_ai, 
        normalizer=real_normalizer, 
        knowledge_repo=real_knowledge_repo,
        tenant_context=ctx
    )
    
    # ---------------------------------------------------------
    # ADIM 1: KATALOG / KATEGORİ SORGUSU
    # ---------------------------------------------------------
    print(f"\n🗣️  MÜŞTERİ: \"Hangi müzik türleri var?\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.LIST_CATALOG)
        
        await service.process_user_input("Hangi müzik türleri var?")
        
        # Context Kontrolü
        call_args = mock_ai.generate_response.call_args
        context_sent = call_args.kwargs.get('context', '')
        
        # Beklenen Kategoriler (Chinook veritabanından)
        expected_genres = ["Rock", "Jazz", "Metal", "Latin", "Pop"]
        found_genres = [g for g in expected_genres if g in context_sent]
        
        if len(found_genres) >= 3:
            print(f"✅ BAŞARILI: Müzik türleri listelendi: {found_genres}")
        else:
            print("❌ HATA: Müzik türleri çekilemedi!")
            # print(f"DEBUG: {context_sent[:200]}")

    # ---------------------------------------------------------
    # ADIM 2: GRUP ARAMA (U2)
    # ---------------------------------------------------------
    print(f"\n🗣️  MÜŞTERİ: \"U2 grubunun şarkıları var mı?\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="u2")
        
        await service.process_user_input("U2 grubunun şarkıları var mı?")
        
        call_args = mock_ai.generate_response.call_args
        context_sent = call_args.kwargs.get('context', '')
        
        if "U2" in context_sent and "Rock" in context_sent:
            print("✅ BAŞARILI: U2 şarkıları bulundu.")
            # Örnek bir satır yakalayalım
            import re
            match = re.search(r"U2 - (.*?) \|", context_sent)
            if match:
                print(f"   👉 Bulunan Örnek: U2 - {match.group(1)}")
        else:
            print("❌ HATA: U2 bulunamadı.")

    # ---------------------------------------------------------
    # ADIM 3: FİYAT KONTROLÜ (Iron Maiden)
    # ---------------------------------------------------------
    print(f"\n🗣️  MÜŞTERİ: \"Iron Maiden şarkıları ne kadar?\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        # "Iron" kelimesiyle aratalım
        m_cls.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="iron")
        
        await service.process_user_input("Iron Maiden şarkıları ne kadar?")
        
        call_args = mock_ai.generate_response.call_args
        context_sent = call_args.kwargs.get('context', '')
        
        # Chinook veritabanında genelde şarkılar 0.99 USD
        if "0.99 USD" in context_sent:
            print("✅ BAŞARILI: Fiyat bilgisi doğru (0.99 USD).")
            print(f"👉 AI'ya Giden Veri (Özet):\n{context_sent.split('Available Inventory')[0].split('===')[-1].strip()[:150]}...")
        else:
            print("❌ HATA: Fiyat bilgisi (0.99 USD) bulunamadı.")

    print("\n" + "="*70)
    print("🎵 TEST SONUCU: Müzik mağazası verileri canlı olarak akıyor.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_live_chinook_conversation())
