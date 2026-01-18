import io
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from app.main import app

# Simulate the test environment
with patch("app.main.GroqAIService") as MockGroq, \
     patch("app.main.GeminiAIService") as MockGemini, \
     patch("app.main.AssistantService") as MockAssistant, \
     patch("app.main.HedefRepository") as MockRepo, \
     patch("app.main.get_memory") as mock_memory_getter, \
     patch("edge_tts.Communicate") as mock_tts:
    
    # Setup Mocks
    mock_ai = MockGroq.return_value
    mock_asst = MockAssistant.return_value
    mock_repo = MockRepo.return_value
    
    mock_ai.client.audio = MagicMock()
    trans = MagicMock()
    trans.text = "Metallica çal"
    mock_ai.client.audio.transcriptions.create = AsyncMock(return_value=trans)
    
    mock_asst.process_user_input = AsyncMock(return_value={
        "user_text": "Metallica çal",
        "ai_response": "Metallica çalınıyor.",
        "intent": "MUSIC_SEARCH",
        "sentiment": "NEUTRAL",
        "context_used": "..."
    })
    
    async def fake_stream():
        yield {"type": "audio", "data": b"fake"}
    mock_tts_instance = mock_tts.return_value
    mock_tts_instance.stream = fake_stream
    
    mock_mem = MagicMock()
    mock_mem.can_accept_input.return_value = True
    mock_mem.get_context.return_value = ""
    mock_mem.is_first_message.return_value = False
    mock_memory_getter.return_value = mock_mem
    
    mock_repo.get_safe_schema_summary.return_value = "Mock Schema"

    with TestClient(app) as client:
        files = {"file": ("test.webm", io.BytesIO(b"fake"), "audio/webm")}
        response = client.post("/talk", files=files, data={"session_id": "test"})
        print(f"Status: {response.status_code}")
        print(f"Headers: {response.headers.get('content-type')}")
        print(f"Body: {response.text}")
