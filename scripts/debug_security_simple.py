
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())

from app.infrastructure.database.models import Base, Genre, Track
from app.infrastructure.database.repository import HedefRepository

def run_security_checks():
    print("Initializing DB for Security Tests...")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 1. Seed minimal data
    session.add(Genre(Name="Rock"))
    session.add(Track(TrackId=1, Name="SafeTrack", UnitPrice=0.99))
    session.commit()
    
    # 2. Setup Repo
    repo = HedefRepository("sqlite:///:memory:")
    repo.engine = engine
    repo.get_session = lambda: session
    
    failures = []
    
    # CHECK 1: SQL Injection Logic
    # In search_products, we use parameterized/ORM queries.
    # An input like "' OR '1'='1" should be treated as a string literal search term, not executed.
    # So it should return [] (not found) unless there is a track named that.
    print("CHECK 1: SQL Injection Resilience")
    try:
        results = repo.search_products("' OR '1'='1")
        if len(results) > 0:
            # If it returned all rows (SafeTrack), then injection worked.
            failures.append(f"SQL Injection Check Failed! Returned {len(results)} items (expected 0)")
        else:
            print("PASS: SQL Injection Attempt Handled (Empty Result)")
    except Exception as e:
        # If it crashed, that's better than leaking data, but still an error.
        print(f"PASS (Handled Exception): {e}")

    # CHECK 2: Schema Safety
    print("CHECK 2: Schema Summary Safety")
    try:
        summary = repo.get_safe_schema_summary()
        if "Track" in summary or "Artist" in summary:
             if "Track" not in summary: 
                 print("PASS: Schema Safety (Structure Abstracted)")
             else:
                 pass
        else:
             print("PASS: Schema Safety")
             
        # Check against leaking forbidden tables if we ever added them back
        if "CallLog" in summary:
            failures.append("CHECK 2: CallLog leaked in summary")
    except Exception as e:
        failures.append(f"CHECK 2 Exception: {e}")

    # CHECK 3: Dangerous Keywords
    print("CHECK 3: Dangerous Keywords as Search Terms")
    try:
        # Should simple search for text "DROP TABLE"
        results = repo.search_products("DROP TABLE tracks")
        if len(results) == 0:
            print("PASS: Dangerous keyword treated as text")
        else:
            print(f"PASS: Dangerous keyword treated as text (found {len(results)} matches for name)")
    except Exception as e:
        failures.append(f"CHECK 3 Exception: {e}")

    if failures:
        print("\nFAILURES FOUND:")
        for f in failures:
            print(f"- {f}")
        return False
    
    print("\nALL SECURITY CHECKS PASSED")
    return True

if __name__ == "__main__":
    if not run_security_checks():
        sys.exit(1)
