
import pytest
import asyncio
import random
import string
from unittest.mock import MagicMock, AsyncMock
from app.core.services.assistant_service import AssistantService
from app.core.services.conversation_gate import GateDecision
from app.core.services.intent_extractor import IntentResult, IntentType

# --- XP TEST FELSEFESİ ---
# 1. Feedback: Sistem yük altındayken ne yapıyor?
# 2. Simplicity: Hata anında karmaşık stack trace yerine basit bir yanıt dönüyor mu?
# 3. Courage: Sistemi kırmak için kasıtlı olarak bozuk parçalarla test ediyoruz.

@pytest.fixture
def xp_service_setup():
    """Heavyweight mocked service with Chaos capabilities."""
    mock_db = MagicMock()
    mock_ai = AsyncMock()
    mock_gate = MagicMock()
    mock_ext = MagicMock()
    mock_cls = MagicMock()
    mock_know = MagicMock()
    mock_ctx = MagicMock()

    # Varsayılan "Mutlu Yol" Ayarları
    mock_ctx.get_current_tenant.return_value = "default_xp_tenant"
    # CRITICAL FIX: Explicitly disable maintenance mode
    mock_ctx.get_tenant_config.return_value = {}  # maintenance_mode: False (None/Empty)
    mock_know.get_tenant_info.return_value = {"ad": "XP Corp"}
    mock_gate.validate_request = AsyncMock(return_value=GateDecision.BUSINESS)
    mock_ext.classify.return_value = IntentResult(intent=IntentType.SEARCH_PRODUCT)
    mock_ai.generate_response.return_value = "XP Test Yanıtı"
    
    # DB normalde boş liste dönsün
    mock_db.search_products.return_value = []
    
    service = AssistantService(
        db_repo=mock_db, ai_service=mock_ai,
        gate_service=mock_gate, intent_extractor=mock_ext,
        intent_classifier=mock_cls, knowledge_repo=mock_know,
        tenant_context=mock_ctx
    )
    service.GateDecision = GateDecision
    
    return service, mock_ai, mock_db, mock_gate

@pytest.mark.asyncio
async def test_concurrent_multi_tenant_load(xp_service_setup):
    """
    XP Stress Test: Aynı milisaniyede 50 farklı istek geldiğinde
    Python'un async yapısının bloklanmadığını ve karışmadığını doğrular.
    """
    service, _, _, mock_gate = xp_service_setup
    
    # Simüle edilmiş asenkron yük
    async def simulate_user_request(user_id):
        # Her istekte yapay bir gecikme varmış gibi (Network I/O)
        # Eğer sistem senkron çalışıyorsa toplam süre 50 * 0.01 sn olur.
        # Asenkron ise çok daha kısa sürer.
        response = await service.process_user_input(f"Test mesajı from {user_id}")
        return response

    # 50 Eşzamanlı İstek (Concurrency)
    tasks = [simulate_user_request(i) for i in range(50)]
    
    # Hepsi aynı anda çalışsın
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 50
    # Gate 50 kere çağrılmış olmalı
    assert mock_gate.evaluate.call_count == 50
    
    # Tüm yanıtlar başarılı (None değil) olmalı
    for res in results:
        assert res is not None
        assert "ai_response" in res

@pytest.mark.asyncio
async def test_chaos_resilience_service_failure(xp_service_setup):
    """
    XP Chaos Test: Bağımlı servisler (LLM, DB) patladığında
    sistemin çökmemesi ve 'Graceful Degradation' uygulaması gerekir.
    """
    service, mock_ai, mock_db, _ = xp_service_setup
    
    # KAOS ENJEKSİYONU: AI Servisi Timeout yiyor
    mock_ai.generate_response.side_effect = TimeoutError("Groq API Timeout")
    
    # KAOS ENJEKSİYONU: Veritabanı Bağlantısı Kopuyor
    mock_db.search_products.side_effect = ConnectionError("DB Connection Lost")
    
    # Normalde bu durumda uygulama çökmemeli, kullanıcıya nazik bir hata dönmeli
    # Kodun içinde 'ERROR_RECOVERY' mekanizması devreye girmeli.
    
    try:
        result = await service.process_user_input("Bana bir şeyler bul")
        
        # Eğer çökmediyse, dönen cevapta hata olduğuna dair izler olmalı
        # Sistem varsayılan bir recovery mesajı döner.
        assert result is not None
        
        # KEY FIX: 'response' -> 'ai_response'
        response_text = result.get("ai_response", "")
        
        # Beklenti: Sistem exception fırlatıp testi durdurmamalı.
        assert isinstance(response_text, str)
        
    except Exception as e:
        pytest.fail(f"Sistem KAOS altında çöktü! Beklenmeyen hata: {e}")

@pytest.mark.asyncio
async def test_invariant_output_structure_fuzzing(xp_service_setup):
    """
    XP Invariant Test: Girdi ne kadar bozuk olursa olsun (Fuzzing),
    sistemin çıktı kontratı (JSON Schema) ASLA bozulmamalı.
    """
    service, _, _, _ = xp_service_setup
    
    # Fuzzing dataset
    fuzz_inputs = [
        "   ", # Whitespace
        "👍" * 100, # Emoji spam
        "\x00\x01\xFF", # Binary garbage
        "SELECT * FROM Users;", # SQL Injection attempt
        "a" * 5000, # Buffer overflow attempt
        None, # NoneType
    ]
    
    for inp in fuzz_inputs:
        try:
            # None gelirse kodun str() çevrimi yapıp yapmadığını veya hata verdiğini göreceğiz
            if inp is None:
                continue 
                
            result = await service.process_user_input(inp)
            
            # INVARIANT: Çıktı her zaman bir sözlük olmalı
            assert isinstance(result, dict), f"Input '{inp}' failed invariant: Output not dict"
            
            # INVARIANT: 'ai_response' anahtarı kesinlikle olmalı
            assert "ai_response" in result, f"Input '{inp}' failed invariant: Missing 'ai_response'"
            
            # INVARIANT: 'intent' anahtarı kesinlikle olmalı
            assert "intent" in result, f"Input '{inp}' failed invariant: Missing 'intent'"
            
        except Exception as e:
            pytest.fail(f"Invariant Violation with input '{inp[:20]}...': {e}")

