import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Force UTF-8 Output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.ai.groq_service import GroqAIService
from app.core.services.assistant_service import AssistantService

async def check_personality():
    print("Checking AI Personality Rules...")
    ai = GroqAIService(api_key="fake")
    prompt = ai._get_system_prompt()
    
    if "SOHBET MODU" not in prompt: raise Exception("Missing Chat Mode Rule")
    if "GÖREVE ODAKLA" not in prompt: raise Exception("Missing Task Focus Rule")
    if "PROFESYONEL" not in prompt: raise Exception("Missing Professional Rule")
    print("✅ System Prompt contains all required rules.")

async def check_social_logic():
    print("Checking Assistant Social Logic...")
    mock_db = MagicMock()
    mock_db.search_products.return_value = []
    mock_db.list_all_products.return_value = []
    mock_db.get_unique_genres.return_value = []
    
    from unittest.mock import MagicMock, AsyncMock

    mock_ai = MagicMock()
    mock_ai.generate_response = AsyncMock(return_value="OK")
    
    service = AssistantService(db_repo=mock_db, ai_service=mock_ai)
    # Mock normalizer
    service.normalizer = MagicMock() 
    service.normalizer.normalize.return_value = "naber"
    
    await service.process_user_input("Naber")
    
    if not mock_ai.generate_response.called:
        raise Exception("AI Generate Response was NOT called!")

    call_args = mock_ai.generate_response.call_args
    # call_args is (args, kwargs) tuple in recent python versions, 
    # but mock_ai.generate_response.call_args.kwargs is safer
    
    _, kwargs = call_args
    context = kwargs.get('context', '')
    
    # Check for relaxed matching
    if "sohbet" not in context:
        print(f"FAILED CONTEXT: {context}")
        raise Exception("Assistant did not trigger social context!")
    print("✅ Assistant correctly handles empty results for social queries.")

def check_voice_files():
    print("Checking Voice Feature Integrity...")
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "interactive_mode.py")
    with open(path, "r", encoding="utf-8") as f: content = f.read()
    
    if "import speech_recognition" not in content: raise Exception("Voice lib missing")
    if "listen_mic" not in content: raise Exception("Mic logic missing")
    print("✅ interactive_mode.py has all voice components.")

async def main():
    print("🚀 STARTING SAFETY CHECKS...")
    
    # 1. Personality
    try:
        await check_personality()
    except Exception as e:
        print(f"❌ PERSONALITY CHECK FAILED: {e}")
        import traceback; traceback.print_exc()

    # 2. Social Logic
    try:
        await check_social_logic()
    except Exception as e:
        print(f"❌ SOCIAL LOGIC CHECK FAILED: {e}")
        import traceback; traceback.print_exc()

    # 3. Voice Files
    try:
        check_voice_files()
    except Exception as e:
        print(f"❌ VOICE FILE CHECK FAILED: {e}")
        import traceback; traceback.print_exc()
        
    print("\n🏁 Safety Checks Completed.")

if __name__ == "__main__":
    asyncio.run(main())
