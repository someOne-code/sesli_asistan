
import sys
import os
import io
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

sys.path.append(os.getcwd())

# Import app
from app.main import app

def debug_e2e():
    print("Testing API E2E (Mocked)...")
    
    # We must patch where they are USED/INSTANTIATED in lifespan
    # app.main imports these classes, so we patch 'app.main.GroqAIService' etc.
    
    with patch("app.main.GroqAIService") as MockGroq, \
         patch("app.main.AssistantService") as MockAssistant, \
         patch("app.main.SqliteMusicRepository") as MockRepo, \
         patch("app.main.get_memory") as mock_memory_getter, \
         patch("edge_tts.Communicate") as mock_tts:
        
        # Setup Mocks
        mock_ai_instance = MockGroq.return_value
        mock_assistant_instance = MockAssistant.return_value
        
        # Mock ASR
        mock_ai_instance.client.audio = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.text = "Metallica çal"
        mock_ai_instance.client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
        
        # Mock Logic
        mock_assistant_instance.process_user_input = AsyncMock(return_value={
            "user_text": "Metallica çal",
            "ai_response": "Metallica çalınıyor.",
            "intent": "MUSIC_SEARCH",
            "sentiment": "NEUTRAL"
        })
        
        # Mock TTS
        async def fake_stream():
            yield {"type": "audio", "data": b"fake_audio_chunk"}
        mock_tts.return_value.stream = fake_stream
        
        # Mock Memory
        mock_mem = MagicMock()
        mock_mem.can_accept_input.return_value = True
        mock_mem.get_context.return_value = ""
        mock_mem.is_first_message.return_value = False
        mock_memory_getter.return_value = mock_mem
        
        mock_repo.return_value.get_safe_schema_summary.return_value = "Mock Schema"

        print("Initialized Mocks. Starting Client...")
        
        try:
            with TestClient(app) as client:
                print("Client Started. Sending Request...")
                file_content = b"fake_audio"
                files = {"file": ("test.webm", io.BytesIO(file_content), "audio/webm")}
                
                resp = client.post("/talk", files=files, data={"session_id": "test_session"})
                
                print(f"Response Status: {resp.status_code}")
                if resp.status_code == 200:
                    print("PASS: Status 200")
                else:
                    print(f"FAIL: Status {resp.status_code}")
                    print(resp.json())
                    return False
                    
                content = b"".join(resp.iter_bytes())
                if b"fake_audio_chunk" in content:
                    print("PASS: Audio Stream Verified")
                else:
                    print(f"FAIL: No Audio in response. Length: {len(content)}")
                    return False
                    
                return True
                
        except Exception as e:
            print(f"CRITICAL FAIL: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    if not debug_e2e():
        sys.exit(1)
    print("ALL E2E TESTS PASSED")
