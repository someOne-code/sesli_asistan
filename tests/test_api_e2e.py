"""
End-to-End API Tests for /talk endpoint.
Simulates a full voice interaction cycle without external API calls.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
import io

# We need to import app AFTER mocking potential hard dependencies if they were at module level,
# but here they are in lifespan, so we can import first.
from app.main import app

# client = TestClient(app)  <-- REMOVED: Instantiating globally triggers lifespan/DB/AI startup without mocks!

@pytest.fixture
def mock_services():
    """
    Mock the classes instantiated in lifespan to inject mocks into the app.
    """
    with patch("app.main.GroqAIService") as MockGroq, \
         patch("app.main.GeminiAIService") as MockGemini, \
         patch("app.main.AssistantService") as MockAssistant, \
         patch("app.main.HedefRepository") as MockRepo, \
         patch("app.main.get_memory") as mock_memory_getter, \
         patch("edge_tts.Communicate") as mock_tts:
        
        # 1. Setup Mock Instances
        mock_ai_instance = MockGroq.return_value
        mock_assistant_instance = MockAssistant.return_value
        mock_repo_instance = MockRepo.return_value
        
        # 2. Mock ASR (Voice-to-Text)
        mock_ai_instance.client.audio = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.text = "Metallica çal"
        mock_ai_instance.client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
        
        # 3. Mock Assistant Logic (Text-to-Intent-to-Response)
        mock_assistant_instance.process_user_input = AsyncMock(return_value={
            "user_text": "Metallica çal",
            "ai_response": "Metallica çalınıyor.",
            "intent": "MUSIC_SEARCH",
            "sentiment": "NEUTRAL",
            "context_used": "..."
        })
        
        # 4. Mock TTS (Text-to-Audio)
        async def fake_stream():
            yield {"type": "audio", "data": b"fake_audio_chunk_1"}
            yield {"type": "audio", "data": b"fake_audio_chunk_2"}
            
        mock_tts_instance = mock_tts.return_value
        mock_tts_instance.stream = fake_stream

        # 5. Mock Memory
        mock_mem = MagicMock()
        mock_mem.can_accept_input.return_value = True
        mock_mem.get_context.return_value = ""
        mock_mem.is_first_message.return_value = False
        mock_memory_getter.return_value = mock_mem
        
        # 6. Mock Schema (used in lifespan)
        mock_repo_instance.get_safe_schema_summary.return_value = "Mock Schema"

        yield {
            "ai": mock_ai_instance,
            "assistant": mock_assistant_instance,
            "memory": mock_mem
        }

def test_talk_endpoint_success(mock_services):
    """
    Test successful /talk flow with mocked dependencies.
    """
    # Create valid dummy audio file
    file_content = b"fake_audio_bytes"
    files = {"file": ("test.webm", io.BytesIO(file_content), "audio/webm")}
    
    # Trigger request
    with TestClient(app) as client:
        response = client.post("/talk", files=files, data={"session_id": "test_session"})
    
    # Verify Status
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    
    # Verify Content
    content = b"".join(response.iter_bytes())
    assert b"fake_audio_chunk_1" in content
    assert b"fake_audio_chunk_2" in content
    
    # Verify Interactions
    mock_services["ai"].client.audio.transcriptions.create.assert_called()
    mock_services["assistant"].process_user_input.assert_called()

def test_talk_endpoint_short_input(mock_services):
    """
    Test input too short filter (< 3 chars)
    """
    # Mock ASR to return short text
    mock_transcription = MagicMock()
    mock_transcription.text = "Hi"
    mock_services["ai"].client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
    
    files = {"file": ("test.webm", io.BytesIO(b"short"), "audio/webm")}
    
    with TestClient(app) as client:
        response = client.post("/talk", files=files)
    
    assert response.status_code == 200
    # Should return empty audio
    assert response.content == b""
    # Assistant logic should NOT be called
    mock_services["assistant"].process_user_input.assert_not_called()

def test_talk_endpoint_hallucination_filter(mock_services):
    """
    Test hallucination filtering (e.g. "altyazı")
    """
    mock_transcription = MagicMock()
    mock_transcription.text = "Videoyu beğenmeyi unutmayın altyazı"
    mock_services["ai"].client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)
    
    files = {"file": ("test.webm", io.BytesIO(b"hallucination"), "audio/webm")}
    
    with TestClient(app) as client:
        response = client.post("/talk", files=files)
    
    assert response.status_code == 200
    assert response.content == b""
    mock_services["assistant"].process_user_input.assert_not_called()
