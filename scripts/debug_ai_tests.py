
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

from app.infrastructure.ai.groq_service import GroqAIService

async def debug_ai():
    print("Testing AI Manager (Mocked)...")
    
    # Setup Service with Mock Client
    service = GroqAIService(api_key="fake")
    service.client = MagicMock()
    service.client.chat.completions.create = AsyncMock()
    
    # Test 1: Intent
    print("Test 1: Intent Detection...", end="")
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "MUSIC_SEARCH"
    service.client.chat.completions.create.return_value = mock_resp
    
    intent = await service.determine_intent("Metallica çal")
    if intent == "MUSIC_SEARCH":
        print("PASS")
    else:
        print(f"FAIL: {intent}")
        return False

    # Test 2: Command
    print("Test 2: Command Parsing...", end="")
    mock_resp.choices[0].message.content = '{"action": "GET_CHEAPEST", "params": {}}'
    service.client.chat.completions.create.return_value = mock_resp
    
    cmd = await service.generate_command("En ucuz ne var?")
    if cmd["action"] == "GET_CHEAPEST":
        print("PASS")
    else:
        print(f"FAIL: {cmd}")
        return False
        
    # Test 3: Safeguard
    print("Test 3: SQL Safeguard...", end="")
    mock_resp.choices[0].message.content = "SELECT * FROM Track"
    service.client.chat.completions.create.return_value = mock_resp
    
    resp = await service.generate_response("hack me")
    if "SELECT" not in resp and "Müzikle ilgili" in resp:
        print("PASS")
    else:
        print(f"FAIL: {resp}")
        return False

    print("ALL AI TESTS PASSED")
    return True

if __name__ == "__main__":
    asyncio.run(debug_ai())
