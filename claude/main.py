import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import edge_tts
import io
import os
import asyncio
import uuid
from typing import Optional
import json
from datetime import datetime

# Load environment variables
load_dotenv()

from config import settings, logger, LogEmoji
from database import DatabaseManager
from safe_service import SafeService
from ai_manager import AIManager
from business_layer import (
    MusicCatalogBusiness,
    ConversationBusiness,
    RecommendationBusiness
)
from memory import ConversationMemory, SessionManager
from utils import TextUtils, ValidationUtils
from conversation_logger import conversation_logger  # YENİ: TXT logger

# ==================== KATMANLI MİMARİ BAŞLATMA ====================

# 1. Data Access Layer
db_manager = DatabaseManager(settings.DB_NAME)

# 2. Service Layer (Güvenlik katmanı)
safe_service = SafeService(db_manager)

# 3. Business Layer (İş mantığı katmanı)
music_business = MusicCatalogBusiness(safe_service)
conversation_business = ConversationBusiness()
recommendation_business = RecommendationBusiness(music_business)

# 4. AI Layer
ai_manager = AIManager(safe_service)

# 5. Session Management
session_manager = SessionManager(redis_url=os.getenv("REDIS_URL"))
global_memory = ConversationMemory(
    redis_url=os.getenv("REDIS_URL"), 
    session_id=settings.DEFAULT_SESSION_ID
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle"""
    # Startup
    logger.info(f"{LogEmoji.ROCKET} Application starting up...")
    logger.info(f"{LogEmoji.CHECK} Katmanlı mimari başlatılıyor...")
    logger.info(f"{LogEmoji.CHECK} → Data Access Layer: HAZIR")
    logger.info(f"{LogEmoji.CHECK} → Service Layer: HAZIR")
    logger.info(f"{LogEmoji.CHECK} → Business Layer: HAZIR")
    logger.info(f"{LogEmoji.CHECK} → AI Layer: HAZIR")
    logger.info(f"{LogEmoji.CHECK} → Conversation Logger: HAZIR")
    
    # Test Database Connection
    try:
        if db_manager.test_connection():
            logger.info(f"{LogEmoji.CHECK} Database connected")
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Database initialization error: {e}")
    
    # Initialize AI Persona
    try:
        ai_manager.initialize_persona()
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Failed to initialize AI persona: {e}")
    
    logger.info(f"{LogEmoji.CHECK} Application ready to accept requests")
    
    yield
    
    # Shutdown
    logger.info(f"[SHUTDOWN] Application shutting down...")
    global_memory.clear()
    session_manager.clear_all_sessions()
    logger.info(f"{LogEmoji.CHECK} Cleanup completed")


app = FastAPI(
    title="AI Music Assistant - Katmanlı Mimari + TXT Logging",
    description="Voice-enabled AI assistant with layered architecture and file logging",
    version="3.1.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Music Assistant",
        "version": "3.1.0",
        "features": ["layered_architecture", "txt_logging", "database_logging"],
        "layers": [
            "Presentation",
            "AI",
            "Business",
            "Service", 
            "Data Access",
            "Database",
            "Memory",
            "Utility",
            "Configuration"
        ]
    }


@app.post("/talk")
async def talk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    session_id: str = Form(settings.DEFAULT_SESSION_ID)
):
    """Main voice interaction endpoint with TXT logging"""
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] {LogEmoji.MIC} New /talk request - session: {session_id}")
    
    try:
        # Validate session ID
        if not ValidationUtils.is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        # Get or create session memory
        memory = session_manager.get_session(session_id)
        
        # Read audio file
        audio_content = await file.read()
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = "input.webm"
        
        # 1. Speech to Text
        try:
            transcription = ai_manager.client.audio.transcriptions.create(
                file=audio_buffer, 
                model=settings.WHISPER_MODEL, 
                language=settings.WHISPER_LANGUAGE
            )
            user_text = transcription.text.strip()
            logger.info(f"[{request_id}] {LogEmoji.WRITE} Transcription: {user_text}")
        except Exception as e:
            logger.error(f"[{request_id}] {LogEmoji.ERROR} Transcription failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Transcription failed", "detail": str(e)}
            )
        
        # Filter noise
        if TextUtils.is_noise(user_text, settings.NOISE_PHRASES, settings.MIN_INPUT_LENGTH):
            logger.info(f"[{request_id}] {LogEmoji.SOUND_OFF} Input ignored (noise)")
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "reason": "noise_detected"}
            )
        
        # Sanitize input
        user_text = TextUtils.sanitize_input(user_text)
        
        # 2. Detect Intent
        intent = ai_manager.determine_intent(user_text)
        logger.info(f"[{request_id}] {LogEmoji.TARGET} Intent: {intent}")
        
        # 3. Analyze Sentiment
        sentiment = ai_manager.analyze_sentiment(user_text)
        logger.info(f"[{request_id}] {LogEmoji.SMILE} Sentiment: {sentiment}")
        
        # 4. Process based on intent (Business Layer logic)
        context_data = ""
        
        if intent == "FORBIDDEN_DATA":
            context_data = "FORBIDDEN_DATA"
            logger.warning(f"[{request_id}] {LogEmoji.WARNING} Forbidden data requested")
        
        elif intent == "OUT_OF_SCOPE":
            context_data = "OUT_OF_SCOPE"
            logger.info(f"[{request_id}] {LogEmoji.WARNING} Out of scope request")
        
        elif intent == "COMPANY_INFO":
            context_data = "COMPANY_INFO_REQUEST"
            logger.info(f"[{request_id}] {LogEmoji.INFO} Company info request")
        
        elif intent == "MUSIC_QUERY":
            history_context = memory.get_context(last_n=5)
            action_data = ai_manager.parse_music_query(user_text, context_history=history_context)
            logger.info(f"[{request_id}] {LogEmoji.SEARCH} Action: {action_data.get('action')}")
            
            action_name = action_data.get('action', 'NOT_AVAILABLE')
            action_params = action_data.get('params', {})
            
            # Business Layer routing (simplified for brevity)
            if action_name in ['SEARCH_TRACKS', 'SEARCH_ALBUMS', 'SEARCH_ARTISTS']:
                result = music_business.search_music(
                    keyword=action_params.get('keyword', ''),
                    search_type=action_name.split('_')[1].lower(),
                    limit=action_params.get('limit', 5)
                )
                context_data = json.dumps(result, ensure_ascii=False)
            
            elif action_name == 'GET_CHEAPEST_TRACKS':
                result = music_business.get_budget_friendly_tracks(
                    genre=action_params.get('genre'),
                    max_price=action_params.get('max_price', 1.0)
                )
                context_data = json.dumps(result, ensure_ascii=False)
            
            elif action_name != 'NOT_AVAILABLE':
                result = safe_service.execute_action(action_name, action_params)
                if result['status'] == 'success':
                    context_data = json.dumps(result['data'], ensure_ascii=False)
                else:
                    context_data = "NOT_AVAILABLE"
        
        else:  # CHAT
            logger.info(f"[{request_id}] {LogEmoji.CHAT} Chat intent")
        
        # 5. Generate Response
        ai_response = ai_manager.generate_response(user_text, context=context_data, intent=intent)
        logger.info(f"[{request_id}] {LogEmoji.CHAT} AI Response: {ai_response[:100]}...")
        
        # 6. Update Memory
        memory.add_turn(user_text, ai_response)
        logger.info(f"[{request_id}] {LogEmoji.MEMORY} Memory updated ({memory.count_turns()} turns)")
        
        # 7. KAYDETME - İKİ YÖNTEM (Database + TXT)
        
        # A) Database'e kaydet (internal - AI görmez)
        background_tasks.add_task(
            safe_service._log_interaction_to_db,
            customer_text=user_text,
            ai_response=ai_response,
            sentiment=sentiment,
            summary=None,
            session_id=session_id,
            intent=intent
        )
        
        # B) TXT dosyasına kaydet (YENİ!)
        background_tasks.add_task(
            conversation_logger.save_conversation,
            session_id=session_id,
            customer_text=user_text,
            ai_response=ai_response,
            sentiment=sentiment,
            intent=intent,
            timestamp=datetime.now()
        )
        
        # 8. TTS Streaming
        async def audio_stream_generator():
            try:
                communicate = edge_tts.Communicate(ai_response, settings.SES_MODELI)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]
            except Exception as e:
                logger.error(f"[{request_id}] {LogEmoji.ERROR} TTS error: {e}")
        
        logger.info(f"[{request_id}] {LogEmoji.SPEAKER} Streaming audio response")
        return StreamingResponse(audio_stream_generator(), media_type="audio/mpeg")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] {LogEmoji.ERROR} Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )


@app.post("/end-call")
async def end_call(
    background_tasks: BackgroundTasks,
    session_id: str = Form(settings.DEFAULT_SESSION_ID)
):
    """End conversation with TXT summary"""
    logger.info(f"{LogEmoji.PHONE} Ending call for session: {session_id}")
    
    try:
        if not ValidationUtils.is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        memory = session_manager.get_session(session_id)
        context = memory.get_context()
        
        if not context:
            return {
                "status": "ok",
                "message": "No conversation to summarize",
                "session_id": session_id
            }
        
        # Generate summary
        summary = ai_manager.generate_summary(context)
        
        # Business Layer: Engagement analysis
        turns = memory.get_all_turns()
        avg_length = sum(len(t.get('user', '')) for t in turns) / len(turns) if turns else 0
        
        engagement = conversation_business.calculate_engagement_score(
            turn_count=len(turns),
            avg_response_length=int(avg_length)
        )
        
        logger.info(f"{LogEmoji.WRITE} Engagement: {engagement['score']} ({engagement['category']})")
        
        # KAYDETME - İKİ YÖNTEM
        
        # A) Database'e kaydet
        background_tasks.add_task(
            safe_service._log_interaction_to_db,
            customer_text="[SESSION_END]",
            ai_response="[SESSION_END]",
            sentiment="NEUTRAL",
            summary=summary,
            session_id=session_id,
            intent="SESSION_END"
        )
        
        # B) TXT dosyasına özet kaydet (YENİ!)
        background_tasks.add_task(
            conversation_logger.save_session_summary,
            session_id=session_id,
            summary=summary,
            total_turns=len(turns),
            engagement_score=engagement
        )
        
        # Get TXT file path
        txt_file = conversation_logger.get_session_log_path(session_id)
        
        # Clear session
        memory.clear()
        session_manager.delete_session(session_id)
        
        return {
            "status": "ok",
            "summary": summary,
            "engagement": engagement,
            "session_id": session_id,
            "log_file": txt_file,
            "message": f"Görüşme notları kaydedildi: {txt_file}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Error ending call: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ==================== YENİ: TXT LOG ENDPOINT'LERİ ====================

@app.get("/logs/txt/{session_id}")
async def get_txt_log(session_id: str, date: Optional[str] = None):
    """
    Bir oturumun TXT log dosyasını görüntüle
    
    Args:
        session_id: Oturum ID'si
        date: YYYYMMDD formatında tarih (opsiyonel)
    """
    try:
        if not ValidationUtils.is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # Tarih parse
        date_obj = None
        if date:
            date_obj = datetime.strptime(date, "%Y%m%d")
        
        # Log dosyasını oku
        content = conversation_logger.read_session_log(session_id, date_obj)
        
        if not content:
            raise HTTPException(status_code=404, detail="Log file not found")
        
        return {
            "session_id": session_id,
            "date": date or datetime.now().strftime("%Y%m%d"),
            "content": content
        }
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYYMMDD")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Error retrieving log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/txt/{session_id}/download")
async def download_txt_log(session_id: str, date: Optional[str] = None):
    """TXT log dosyasını indir"""
    try:
        if not ValidationUtils.is_valid_session_id(session_id):
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        date_obj = None
        if date:
            date_obj = datetime.strptime(date, "%Y%m%d")
        
        filepath = conversation_logger.get_session_log_path(session_id, date_obj)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Log file not found")
        
        return FileResponse(
            path=filepath,
            media_type='text/plain',
            filename=os.path.basename(filepath)
        )
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Error downloading log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/txt/list")
async def list_txt_logs(session_id: Optional[str] = None):
    """Tüm TXT log dosyalarını listele"""
    try:
        files = conversation_logger.list_session_logs(session_id)
        
        return {
            "count": len(files),
            "files": files,
            "directory": conversation_logger.log_directory
        }
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Error listing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/logs/txt/cleanup")
async def cleanup_old_logs(days: int = 30):
    """Eski log dosyalarını temizle"""
    try:
        deleted = conversation_logger.cleanup_old_logs(days_to_keep=days)
        
        return {
            "status": "ok",
            "deleted_files": deleted,
            "message": f"{deleted} adet eski log dosyası silindi"
        }
    except Exception as e:
        logger.error(f"{LogEmoji.ERROR} Error cleaning logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DİĞER ENDPOINT'LER ====================

@app.get("/health")
async def health_check():
    """Detailed health check"""
    db_healthy = db_manager.test_connection()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "layers": {
            "database": "connected" if db_healthy else "disconnected",
            "service_layer": "ready",
            "business_layer": "ready",
            "ai_layer": "ready" if settings.GROQ_API_KEY else "not configured",
            "txt_logger": "ready"
        },
        "architecture": "9_layers_with_txt_logging"
    }


@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    sessions = session_manager.list_sessions()
    return {
        "active_sessions": len(sessions),
        "session_ids": sessions
    }


if __name__ == "__main__":
    logger.info(f"{LogEmoji.ROCKET} Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"{LogEmoji.CHECK} TXT logging enabled - Files saved to: conversation_logs/")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")