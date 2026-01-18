import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from contextlib import asynccontextmanager
import io
import os
import sys
import edge_tts
import time
import urllib.parse

def log(msg):
    """Print with flush for Windows CMD visibility"""
    print(msg)
    sys.stdout.flush()

def now():
    return round(time.time() * 1000)  # ms

# Yeni yapıdan importlar
# Yeni yapıdan importlar
from app.core.config import settings, logger
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.ai.groq_service import GroqAIService
from app.infrastructure.ai.gemini_service import GeminiAIService
from app.infrastructure.memory import ConversationMemory
from app.core.services.assistant_service import AssistantService
from app.routes import admin_routes
from app.util.fuzzy import normalize_query, is_list_all_query

# Global Service Instances (Dependency Injection Container gibi davranır)
db_repo = None
ai_service = None
assistant_service = None
normalizer = None
sessions = {}

# Import StaticTenantContext for per-request isolation
from app.infrastructure.tenant.static_tenant_context import StaticTenantContext

def get_memory(session_id: str) -> ConversationMemory:
    if session_id not in sessions:
        # Memory şu an Redis URL'sini env'den alıyor, infrastructure içinde
        sessions[session_id] = ConversationMemory(redis_url=os.getenv("REDIS_URL"), session_id=session_id)
    return sessions[session_id]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_repo, ai_service, assistant_service, normalizer
    logger.info("Uygulama başlatılıyor (Katmanlı Mimari)...")
    
    # 1. Altyapı (Infrastructure) Katmanını Başlat
    db_repo = HedefRepository(db_url=settings.DB_NAME)
    
    # AI Sağlayıcı Seçimi
    if settings.AI_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            logger.warning("Gemini Key eksik, Groq'a dönülüyor (Fallback)...")
            ai_service = GroqAIService(api_key=settings.GROQ_API_KEY)
        else:
            logger.info("Yapay Zeka Modu: GOOGLE GEMINI")
            ai_service = GeminiAIService(api_key=settings.GEMINI_API_KEY)
    else:
        logger.info("Yapay Zeka Modu: GROQ (LLAMA)")
        ai_service = GroqAIService(api_key=settings.GROQ_API_KEY)
    
    # 2. Dinamik Şema Keşfi ve Enjeksiyonu (GÜVENLİ MOD)
    safe_schema = db_repo.get_safe_schema_summary()
    ai_service.set_db_schema(safe_schema)
    logger.info(f"Yapay Zekaya Veritabanı Şeması Öğretildi:\n{safe_schema}")
    
    # 3. Text Normalizer (Rule Based) Enjeksiyonu
    from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer
    normalizer = RuleBasedNormalizer()
    
    # 4. Servis (Business Logic) Katmanını Başlat
    assistant_service = AssistantService(db_repo, ai_service, normalizer)
    
    # 4. Admin Routes'a DB erişimi ver
    admin_routes.set_db_repo(db_repo)
    
    yield
    
    logger.info("Uygulama kapatılıyor...")
    sessions.clear()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin routes
app.include_router(admin_routes.router)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()

# --- HALLUCINATION FILTER ---
def is_hallucination(text: str) -> bool:
    bad_phrases = ["altyazı", "izlediğiniz için", "abone ol", "videoyu beğen", "subtitle"]
    silence_phrases = ["evet", "alo", "sesim geliyor mu", "ses deneme"]
    normalized = text.lower().strip()
    
    if len(normalized) < 2: return True
    if any(bp in normalized for bp in bad_phrases): return True
    if normalized.rstrip('.') in silence_phrases: return True
    
    return False

# --- NEW: MULTI-TENANT VOICE DEMO ENDPOINT ---
@app.post("/tenants/{tenant_id}/voice")
async def tenant_voice_interaction(
    tenant_id: str,
    file: UploadFile = File(...),
):
    try:
        t_start = now()
        
        # 1. READ AUDIO
        audio_content = await file.read()
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = file.filename or "input.wav" # Use uploaded filename or safe default
        
        # 2. STT (Groq Whisper Turbo)
        # Using enhanced prompt for domain accuracy
        transcription = await ai_service.client.audio.transcriptions.create(
            file=(audio_buffer.name, audio_buffer.read()), 
            model="whisper-large-v3-turbo",
            prompt="Türkçe konuşma. Müşteri asistanla konuşuyor.",
            language="tr",
            response_format="json",
            temperature=0.0
        )
        user_text = transcription.text.strip()
        print(f"[{tenant_id}] STT: '{user_text}' ({now() - t_start}ms)")

        # 3. HALLUCINATION CHECK
        if is_hallucination(user_text):
            logger.warning(f"Hallucination dropped: {user_text}")
            # Return polite 'Not understood' voice (using existing TTS logic)
            failure_text = "Dediğinizi tam anlayamadım, tekrar eder misiniz?"
            async def failure_stream():
                 communicate = edge_tts.Communicate(failure_text, settings.SES_MODELI)
                 async for chunk in communicate.stream():
                     if chunk["type"] == "audio": yield chunk["data"]
            return StreamingResponse(failure_stream(), media_type="audio/mpeg")

        # 4. SCOPED SERVICE (Tenant Isolation)
        # We perform on-the-fly composition for isolation
        scoped_context = StaticTenantContext(tenant_id)
        
        # Reuse globals, inject scoped context
        scoped_assistant = AssistantService(
            db_repo=db_repo, 
            ai_service=ai_service, 
            normalizer=normalizer,
            tenant_context=scoped_context
        )

        # 5. PROCESS
        # Need conversation history from memory?
        # For this demo, let's use a simple per-tenant memory key
        session_id = f"demo_{tenant_id}"
        memory = get_memory(session_id)
        conversation_history = memory.get_context()
        is_first = memory.is_first_message()

        result = await scoped_assistant.process_user_input(
            user_text, 
            session_id=session_id, 
            conversation_history=conversation_history,
            is_first_message=is_first
        )
        
        ai_response = result["ai_response"]
        print(f"[{tenant_id}] AI: '{ai_response[:50]}...'")

        # Update Memory
        memory.add_turn(user_text, ai_response)

        # 6. TTS (EdgeTTS) - Streaming
        async def response_stream():
            communicate = edge_tts.Communicate(ai_response, settings.SES_MODELI)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        
        return StreamingResponse(
            response_stream(), 
            media_type="audio/mpeg",
            headers={
                "X-Recognized-Text": urllib.parse.quote(user_text), 
                "X-Tenant-ID": tenant_id,
                "X-AI-Response": urllib.parse.quote(ai_response)
            }
        )

    except Exception as e:
        logger.error(f"Voice Error: {e}")
        # Graceful Failure Voice
        error_text = "Şu an teknik bir sorun yaşıyorum, lütfen biraz sonra tekrar deneyin."
        async def error_stream():
             communicate = edge_tts.Communicate(error_text, settings.SES_MODELI)
             async for chunk in communicate.stream():
                 if chunk["type"] == "audio": yield chunk["data"]
        return StreamingResponse(
            error_stream(), 
            media_type="audio/mpeg",
            headers={
                "X-AI-Response": urllib.parse.quote(error_text),
                "X-Recognized-Text": urllib.parse.quote("Sistem Hatası")
            }
        )


@app.post("/talk")
async def talk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    session_id: str = Form("global_demo")
):
    try:
        t_req_start = now()
        print(f"REQ START: {t_req_start}")
        
        # STATE CHECK - Only accept in LISTENING state
        memory = get_memory(session_id)
        if not memory.can_accept_input():
            logger.warning(f"[STATE] /talk REJECTED - state={memory.get_state()}")
            async def empty_audio():
                yield b''
            return StreamingResponse(empty_audio(), media_type="audio/mpeg")
        
        # Transition to THINKING
        memory.set_state("THINKING")
        
        audio_content = await file.read()
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = "input.webm"
        
        # Enhanced Whisper prompt with music vocabulary to improve transcription accuracy
        transcription = await ai_service.client.audio.transcriptions.create(
            file=audio_buffer,
            model="whisper-large-v3-turbo",
            prompt="Müzik mağazası konuşması. Kelimeler: müzik, şarkı, albüm, sanatçı, rock, pop, jazz, metal, klasik, fiyat, ücret, satın al, dinle, çal, Queen, Metallica, AC/DC, tür, genre.",
            language="tr",
            temperature=0.0  # More deterministic for better accuracy
        )
        print(f"ASR DONE: {now() - t_req_start} ms")
        user_text = transcription.text.strip()
        
        
        # Hallucination filter
        bad_phrases = ["altyazı", "izlediğiniz için", "abone ol", "videoyu beğen"]
        if any(bp in user_text.lower() for bp in bad_phrases):
             logger.warning(f"Hallucination ignored (phrase): {user_text}")
             memory.force_listening()  # Reset state
             async def empty_audio():
                 yield b''
             return StreamingResponse(empty_audio(), media_type="audio/mpeg")
              
        silence_hallucinations = ["evet", "evet.", "alo", "alo.", "sesim geliyor mu", "sesim geliyor mu?"]
        if user_text.lower().strip() in silence_hallucinations:
             logger.warning(f"Hallucination ignored (silence): {user_text}")
             memory.force_listening()  # Reset state
             async def empty_audio():
                 yield b''
             return StreamingResponse(empty_audio(), media_type="audio/mpeg")

        # === VERBOSE LOGGING START ===
        log("=" * 60)
        log(f"[RAW TRANSCRIPTION]: {user_text}")
        
        # Apply fuzzy normalization
        normalized_text = normalize_query(user_text)
        log(f"[NORMALIZED TEXT]: {normalized_text}")
        
        # Check for LIST_ALL intent
        list_all_intent = is_list_all_query(normalized_text)
        log(f"[LIST_ALL INTENT]: {list_all_intent}")
        log("=" * 60)
        # === VERBOSE LOGGING END ===
        
        logger.info(f"Kullanici dedi ki: {user_text} -> Normalized: {normalized_text}")

        if len(user_text) < 3:
            logger.warning(f"Input too short: {user_text}")
            memory.force_listening()  # Reset state
            async def empty_audio():
                yield b''
            return StreamingResponse(empty_audio(), media_type="audio/mpeg")

        # 2. SIMPLE PIPELINE (Non-streaming for correctness)
        memory = get_memory(session_id)
        conversation_history = memory.get_context()
        
        # Check if this is the first message (for greeting control)
        is_first = memory.is_first_message()
        print(f"[SESSION] is_first_message: {is_first}")
        
        # Call service - get complete response
        result = await assistant_service.process_user_input(
            user_text, 
            session_id, 
            conversation_history,
            is_first_message=is_first
        )
        ai_response = result["ai_response"]
        
        # === VERBOSE AI RESPONSE LOG ===
        log("=" * 60)
        log("[AI RESPONSE]:")
        log(ai_response)
        log("=" * 60)
        
        # Update memory with complete response
        memory.add_turn(user_text, ai_response)
        
        # Log to DB (background)
        background_tasks.add_task(
            db_repo.log_call, 
            user_text, 
            ai_response, 
            result["sentiment"], 
            None, # Summary
            intent=result.get("intent") # Intent
        )

        # 3. TTS - Convert complete response to audio
        async def audio_stream():
            communicate = edge_tts.Communicate(ai_response, settings.SES_MODELI)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        return StreamingResponse(audio_stream(), media_type="audio/mpeg")

    except Exception as e:
        logger.error(f"Hata: {e}")
        return {"error": str(e)}

@app.post("/set-state")
async def set_state(
    session_id: str = Form("global_demo"),
    state: str = Form(...)
):
    """Frontend updates backend state (LISTENING/SPEAKING)"""
    memory = get_memory(session_id)
    
    if state == "LISTENING":
        memory.force_listening()
        return {"status": "ok"}
    
    memory.set_state(state)
    return {"status": "ok"}


@app.post("/end-call")
async def end_call(
    background_tasks: BackgroundTasks,
    session_id: str = Form("global_demo")
):
    try:
        memory = get_memory(session_id)
        context = memory.get_context()
        if not context:
            return {"status": "Empty"}
        
        # summary = await assistant_service.generate_call_summary(context)
        summary = "Özetleme devre dışı (Melody Modu)"
        
        # Loglama
        background_tasks.add_task(db_repo.log_call, "SYSTEM_END_CALL", "N/A", "N/A", summary)
        
        # Dosyaya yazma (Opsiyonel, belki bir FileLogger servisi olabilirdi)
        with open("GORUSME_NOTLARI.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- Oturum {session_id} Özeti ---\n")
            f.write(summary)
            f.write("\n-----------------------------------\n")

        memory.clear()
        if session_id in sessions:
            del sessions[session_id]
            
        return {"status": "OK", "summary": summary}
    except Exception as e:
        return {"error": str(e)}

from pydantic import BaseModel

class ChatRequest(BaseModel):
    user_text: str
    tenant_id: str = "default_tenant"

@app.post("/debug/chat")
async def debug_chat(request: ChatRequest):
    """
    Text-only endpoint for debugging/demo purposes.
    Bypasses STT and TTS steps.
    """
    try:
        # 1. Setup Tenant Context
        # Since we are debugging, we inject the requested tenant directly.
        # This assumes we can override or set the context somehow.
        # For now, let's use the requested tenant_id if passing to a scoped service.
        # But `assistant_service` is global. It gets tenant from `tenant_context`.
        # The global `tenant_context` (if any) might need setting.
        
        # However, looking at the architecture, `AssistantService` logic uses:
        # tenant_id = self.tenant_context.get_current_tenant()
        
        # We need to ensure the context resolves to `request.tenant_id`.
        # Assuming we can use StaticTenantContext similarly to the voice endpoint:
        
        scoped_ctxt = StaticTenantContext(request.tenant_id)
        scoped_svc = AssistantService(
            db_repo=db_repo,
            ai_service=ai_service,
            normalizer=normalizer,
            tenant_context=scoped_ctxt
        )
        
        # 2. Process
        import time
        unique_session = f"debug_{request.tenant_id}_{int(time.time())}"
        
        result = await scoped_svc.process_user_input(
            request.user_text,
            session_id=unique_session
        )
        
        result["debug_tenant"] = request.tenant_id
        
        return result
        
    except Exception as e:
        logger.error(f"Debug Chat Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
