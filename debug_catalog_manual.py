import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.services.assistant_service import AssistantService

async def run():
    print("--- DEBUG CATALOG LOGIC ---")
    mock_db = MagicMock()
    # Setup mocks
    mock_db.get_unique_genres.return_value = ["Rock", "Jazz"]
    mock_db.list_all_products.return_value = []
    mock_db.search_products.return_value = []
    
    mock_ai = AsyncMock()
    mock_ai.generate_response.return_value = "AI Response"
    
    # Init service
    try:
        service = AssistantService(db_repo=mock_db, ai_service=mock_ai)
        print("Service Initialized.")
    except Exception as e:
        print(f"Service Init Failed: {e}")
        return

    query = "Ne tür müzikleriniz var?"
    print(f"Input: '{query}'")
    
    # Act
    try:
        await service.process_user_input(query)
    except Exception as e:
        print(f"Optimization Error during process: {e}")
        # Print traceback?
        import traceback
        traceback.print_exc()
    
    # Report
    print(f"\nRESULTS:")
    print(f"1. list_all_products Called? : {mock_db.list_all_products.called}")
    print(f"2. get_unique_genres Called? : {mock_db.get_unique_genres.called}")
    print(f"3. search_products Called?   : {mock_db.search_products.called}")

if __name__ == "__main__":
    asyncio.run(run())
