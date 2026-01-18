
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil
import gc
from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.database.models import Base, Artist

def run_test():
    print("--- MEMORY LEAK TEST START ---")
    
    # Setup
    db_name = "debug_memory.db"
    if os.path.exists(db_name): os.remove(db_name)
    
    repo = HedefRepository(f"sqlite:///{db_name}")
    Base.metadata.create_all(repo.engine)
    session = repo.get_session()
    session.add(Artist(Name="Leak Artist"))
    session.commit()
    session.close()
    
    process = psutil.Process(os.getpid())
    
    # Warmup
    print("Warming up...")
    for _ in range(50):
        repo.search_products("Leak")
    
    gc.collect()
    initial_mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"Initial Memory: {initial_mem_mb:.2f} MB")
    
    # Stress
    ITERATIONS = 2000
    print(f"Running {ITERATIONS} iterations...")
    for i in range(ITERATIONS):
        repo.search_products("Leak")
        if i % 500 == 0:
            print(f"  Iteration {i}...")
            
    gc.collect()
    final_mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"Final Memory: {final_mem_mb:.2f} MB")
    
    growth = final_mem_mb - initial_mem_mb
    growth = max(0, growth)
    print(f"GROWTH: {growth:.2f} MB")
    
    repo.engine.dispose()
    if os.path.exists(db_name): os.remove(db_name) # Cleanup failure if open? likely fine after dispose
    
    if growth > 50:
        print("❌ FAILURE: Significant memory leak detected.")
        exit(1)
    else:
        print("✅ SUCCESS: Memory usage stable.")
        exit(0)

if __name__ == "__main__":
    run_test()
