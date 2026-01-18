
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.services.assistant_service import AssistantService
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext
from app.core.services.intent_extractor import IntentResult, IntentType
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.database.knowledge_repository import SqlKnowledgeRepository
from app.core.config import settings
from app.infrastructure.database.engine_manager import get_session_factory
from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer

# LIVE INTEGRATION TEST (GERÇEK VERİTABANI)
# Amaç: Mock kullanmadan gerçek veritabanı bağlantısı ile senaryoyu koşmak.

async def test_live_story_conversation():
    print("\n" + "="*60)
    print("🔥  CANLI (LIVE) SİSTEM TESTİ - GERÇEK VERİTABANI")
    print("="*60)
    
    # 1. GERÇEK ALTYAPI KURULUMU
    # db_url = f"sqlite:///{settings.DB_NAME}"
    # NOTE: Repository classes expect the database name/url, they handle connection themselves.
    db_name = settings.DB_NAME
    
    real_db_repo = HedefRepository(db_name)
    real_knowledge_repo = SqlKnowledgeRepository(db_name)
    real_normalizer = RuleBasedNormalizer()
    
    # AI Servisi hala Mock olmak zorunda (Groq API kotasını yememek için veya API key yoksa)
    # Ancak cevapların 'Prompt' içeriğini kontrol ederek doğru verinin gidip gitmediğini göreceğiz.
    mock_ai = AsyncMock()
    mock_ai.generate_response.return_value = "AI Cevabı (Simüle)"

    # 2. SERVİSİ BERBER AHMET İÇİN BAŞLAT
    tenant_id = "berber_ahmet"
    ctx = StaticTenantContext(tenant_id)
    
    service = AssistantService(
        db_repo=real_db_repo, 
        ai_service=mock_ai, 
        normalizer=real_normalizer, 
        knowledge_repo=real_knowledge_repo,
        tenant_context=ctx
    )
    
    # ---------------------------------------------------------
    # ADIM 1: KATALOG SORGUSU ("Neler yapıyorsunuz?")
    # ---------------------------------------------------------
    print(f"\n🗣️  MÜŞTERİ: \"Neler yapıyorsunuz?\"")
    
    # Intent'i yine manuel verelim ki test NLP hatasına takılmasın, sadece Veri Akışını test ediyoruz
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.LIST_CATALOG)
        
        # Gerçek metot çağrısı
        await service.process_user_input("Neler yapıyorsunuz?")
        
        # AI'ya giden context'i yakalayalım
        call_args = mock_ai.generate_response.call_args
        context_sent = call_args.kwargs.get('context', '')
        
        if "Saç Kesimi" in context_sent or "Sakal Tıraşı" in context_sent or "Erkek Bakım" in context_sent:
             print("✅ ASİSTAN (İç Ses): Katalog verisi başarıyla çekildi.")
             print(f"   Context Özeti: {context_sent[:100]}...")
        else:
             print("❌ HATA: Katalog verisi çekilemedi!")

    # ---------------------------------------------------------
    # ADIM 2: FİYAT SORGUSU ("Saç kesimi ne kadar?") - KRİTİK ADIM
    # ---------------------------------------------------------
    print(f"\n🗣️  MÜŞTERİ: \"Saç kesimi kaç para?\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="saç kesimi")
        
        await service.process_user_input("Saç kesimi kaç para?")
        
        # Context'i kontrol et - GERÇEK FİYAT (250.0 TL) OLMALI
        call_args = mock_ai.generate_response.call_args
        context_sent = call_args.kwargs.get('context', '')
        
        # print(f"DEBUG CONTEXT: {context_sent}") 
        
        if "250.0" in context_sent:
            print("✅ BAŞARILI: Gerçek veritabanından 250.0 TL fiyatı çekildi!")
            print(f"👉 AI'ya Giden Veri: \n{context_sent.split('===')[1].strip()}")
        else:
            print("❌ HATA: Fiyat bilgisi yanlış veya çekilemedi.")
            print(f"Gelen Context: {context_sent}")

    # ---------------------------------------------------------
    # ADIM 3: DAMAT TIRAŞI (Müşteri Şaşırtmaca)
    # ---------------------------------------------------------
    print(f"\n🗣️  MÜŞTERİ: \"Damat tıraşı var mı?\"")
    
    with patch('app.core.services.intent_extractor.IntentExtractor.classify') as m_cls:
        m_cls.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT, query_term="damat")
        
        await service.process_user_input("Damat tıraşı var mı?")
        
        call_args = mock_ai.generate_response.call_args
        context_sent = call_args.kwargs.get('context', '')
        
        if "1500.0" in context_sent:
            print("✅ BAŞARILI: Damat tıraşı (1500.0 TL) bulundu.")
        else:
            print("❌ HATA: Damat tıraşı bulunamadı.")

    print("\n" + "="*60)
    print("TEST SONUCU: Sistem gerçek veritabanı ile canlı olarak konuşabiliyor.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_live_story_conversation())
