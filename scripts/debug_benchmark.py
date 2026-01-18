
import asyncio
import time
import sys
import os
from unittest.mock import MagicMock, AsyncMock

sys.path.append(os.getcwd())

from app.core.services.assistant_service import AssistantService
from app.infrastructure.ai.groq_service import GroqAIService
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.database.models import Base, Track, Artist
from sqlalchemy import create_engine

def debug_benchmark_repo():
    print("Initializing In-Memory DB...")
    repo = HedefRepository("sqlite:///:memory:")
    # Seed
    engine = repo.engine
    Base.metadata.create_all(engine)
    
    with repo.get_session() as session:
        # Seed 100 tracks
        for i in range(100):
            t = Track(Name=f"Track {i}", UnitPrice=0.99)
            session.add(t)
        session.commit()
    
    print("Starting Repository Search Benchmark (1000 iter)...")
    start = time.time()
    for _ in range(1000):
        # Search for something that exists
        _ = repo.search_products("Track 50")
    duration = (time.time() - start) * 1000
    print(f"Repo Duration (1000 searches): {duration:.2f} ms")
    
    # Threshold: SQLite memory is fast, should be under 2s for 1000 simple queries
    if duration > 2000:
        print("FAIL: Repo too slow")
        return False
    return True

async def debug_benchmark_service():
    print("Starting Service Overhead Benchmark (100 iter)...")
    repo = HedefRepository("sqlite:///:memory:")
    Base.metadata.create_all(repo.engine) 
    
    mock_ai = MagicMock(spec=GroqAIService)
    mock_ai.generate_command = AsyncMock(return_value={
        "action": "QUERY_DB",
        "params": {}
    })
    mock_ai.generate_response = AsyncMock(return_value="OK")
    
    service = AssistantService(repo, mock_ai)
    
    start = time.time()
    for _ in range(100):
        await service.process_user_input("Track çal")
    duration = (time.time() - start) * 1000
    avg = duration / 100
    print(f"Service Avg Latency: {avg:.4f} ms")
    
    if avg > 50:
        print("FAIL: Service too slow")
        return False
    return True

if __name__ == "__main__":
    try:
        if not debug_benchmark_repo():
            sys.exit(1)
        if not asyncio.run(debug_benchmark_service()):
            sys.exit(1)
        print("BENCHMARKS PASSED")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
