import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import edge_tts
import io
import os
import asyncio
import uuid

from config import settings, logger
from database import DatabaseManager, SafeService
from ai_manager import AIManager
from memory import ConversationMemory

from typing import Dict

# Global instances
db_manager = DatabaseManager(settings.DB_NAME)
safe_service = SafeService(db_manager)
ai_manager = AIManager(db_manager)

# Session Management
sessions: Dict[str, ConversationMemory] = {}

def get_memory(session_id: str) -> ConversationMemory:
    if session_id not in sessions:
        logger.info(f"Creating new memory for session: {session_id}")
        sessions[session_id] = ConversationMemory(redis_url=os.getenv("REDIS_URL"), session_id=session_id)
    return sessions[session_id]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting up...")
    
    # Initialize Database Check
    try:
        # Check if DB exists, if not run init (handled by create_db logic conceptually, 
        # but here we just check connection)
        schema = db_manager.get_schema_info()
        if schema:
            logger.info("Database connected successfully.")
        else:
            logger.warning("Database schema is empty. Running recreation script...")
            try:
                import create_db
                create_db.init_db()
                logger.info("Database created.")
            except Exception as recreate_err:
                logger.error(f"Failed to recreate DB: {recreate_err}")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    # Initialize AI Persona
    await ai_manager.initialize_persona()
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    # Clear all local memories
    for mem in sessions.values():
        mem.clear()
    sessions.clear()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/talk")
async def talk(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    session_id: str = Form("global_demo") # Allow client to send session_id
):
    try:
        # Get memory for this session
        memory = get_memory(session_id)

        # Read audio file
        audio_content = await file.read()
        audio_buffer = io.BytesIO(audio_content)
        audio_buffer.name = "input.webm"
        
        # 1. Speech to Text (Transcribe)
        try:
            transcription = await ai_manager.client.audio.transcriptions.create(
                file=audio_buffer, 
                model="whisper-large-v3", 
                language="tr"
            )
            user_text = transcription.text.strip()
            logger.info(f"Customer said: {user_text}")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {"error": "Transcription failed"}

        # Silence/Noise Filter
        yasakli = ["Altyazı", "altyazı", "Yükleyen", "yükleyen", "Merhaba", "merhaba", ".", ""]
        if len(user_text) < 3 or user_text in yasakli:
            logger.info("Input ignored (too short or noise).")
            return {"status": "ignored"}

        # 2. Parallel AI Tasks: Intent & Sentiment
        # We run these concurrently to optimize latency
        async def get_intent():
            return await ai_manager.determine_intent(user_text)
        
        async def get_sentiment():
            return await ai_manager.analyze_sentiment(user_text)

        intent, sentiment = await asyncio.gather(get_intent(), get_sentiment())
        
        logger.info(f"Intent: {intent} | Sentiment: {sentiment}")

        if "OUT_OF_SCOPE" in intent:
             context_data = "OUT_OF_SCOPE"
        elif "COMPANY_INFO" in intent:
             context_data = "COMPANY_INFO_REQUEST"
        else:
            context_data = ""
            
            # 3. Handle Music Search Intent (formerly SQL)
            if "MUSIC_SEARCH" in intent:
                # Generate Structured Command
                command = await ai_manager.generate_command(user_text)
                logger.info(f"Generated Command: {command}")
                
                action = command.get("action")
                params = command.get("params", {})
                
                # Execute via SafeService
                if action == "SEARCH_TRACKS":
                    context_data = safe_service.search_tracks(params.get("keyword", ""))
                elif action == "GET_TRACKS_BY_GENRE":
                    context_data = safe_service.get_tracks_by_genre(params.get("genre_name", ""))
                elif action == "GET_ALBUM_DETAILS":
                    context_data = safe_service.get_album_details(params.get("album_name", ""))
                elif action == "GET_CHEAPEST":
                    context_data = safe_service.get_cheapest_products()
                elif action == "GET_MOST_EXPENSIVE":
                    context_data = safe_service.get_most_expensive_products()
                else:
                    context_data = "I didn't understand which music to look for."
                
                logger.info(f"Service Result: {context_data}")
            
        # 4. Generate Response
        ai_response = await ai_manager.generate_response(user_text, context=context_data)

        logger.info(f"AI Response: {ai_response}")

        # Update Memory
        memory.add_turn(user_text, ai_response)
        
        # Save Log asynchronously
        background_tasks.add_task(db_manager.log_call, user_text, ai_response, sentiment, None)

        async def audio_stream_generator():
            communicate = edge_tts.Communicate(ai_response, settings.SES_MODELI)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        return StreamingResponse(audio_stream_generator(), media_type="audio/mpeg")

    except Exception as e:
        logger.error(f"Unexpected error in /talk: {e}")
        return {"error": str(e)}

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
        
        # Generate summary
        summary = await ai_manager.generate_summary(context)
        logger.info(f"Call Summary: {summary}")
        
        # Log final summary to DB
        background_tasks.add_task(db_manager.log_call, "SYSTEM_END_CALL", "N/A", "N/A", summary)
        
        # Write summary to text file as requested
        with open("GORUSME_NOTLARI.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- Session {session_id} Summary ---\n")
            f.write(summary)
            f.write("\n-----------------------------------\n")

        memory.clear()
        # Remove from active sessions
        if session_id in sessions:
            del sessions[session_id]
            
        logger.info(f"Call ended and memory cleared for session {session_id}.")
        return {"status": "OK", "summary": summary}
    except Exception as e:
        logger.error(f"Error saving notes: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
