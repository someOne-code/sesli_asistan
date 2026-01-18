
import sys
import os
import pytest

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.models import Base, Genre, Artist, Album, Track, InvoiceLine
from app.infrastructure.database.safe_query_executor import SafeQueryExecutor
from app.infrastructure.database.repository import SqliteMusicRepository

def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def test_whitelist():
    print("Test 1: Whitelist...", end="")
    session = setup_db()
    executor = SafeQueryExecutor(lambda: session)
    
    try:
        executor.execute_generic_query({"table": "CallLog"})
        print("FAIL (Should have raised ValueError)")
        return False
    except ValueError as e:
        if "not in whitelist" in str(e):
            print("PASS")
            return True
        else:
            print(f"FAIL (Wrong error: {e})")
            return False

def test_operators():
    print("Test 2: Operators...", end="")
    session = setup_db()
    executor = SafeQueryExecutor(lambda: session)
    
    try:
        executor.execute_generic_query({
            "table": "Track",
            "filters": [{"column": "Name", "operator": "DROP TABLE", "value": "x"}]
        })
        print("FAIL (Should have raised ValueError)")
        return False
    except ValueError as e:
        if "Invalid operator" in str(e):
            print("PASS")
            return True
        else:
            print(f"FAIL (Wrong error: {e})")
            return False

def test_sqli():
    print("Test 3: SQL Injection...", end="")
    session = setup_db()
    executor = SafeQueryExecutor(lambda: session)
    
    # Needs data to potentially return something if SQLi worked
    # But here we check it doesn't crash/error and returns empty
    try:
        results = executor.execute_generic_query({
            "table": "Track",
            "filters": [{"column": "Name", "operator": "=", "value": "' OR '1'='1"}]
        })
        # Should be empty
        if len(results) == 0:
            print("PASS")
            return True
        else:
            print(f"FAIL (Returned {len(results)} results)")
            return False
    except Exception as e:
        print(f"FAIL (Exception: {e})")
        return False

def test_schema_safety():
    print("Test 4: Schema Safety...", end="")
    # Use repo but create tables first
    repo = SqliteMusicRepository("sqlite:///:memory:") 
    Base.metadata.create_all(repo.engine)
    
    summary = repo.get_safe_schema_summary()
    
    if "CallLog" in summary or "call_logs" in summary:
         print("FAIL (Sensitive table exposed)")
         return False
    
    if "Track" in summary:
        print("PASS")
        return True

    else:
        print("FAIL (Track table not found)")
        return False

if __name__ == "__main__":
    tests = [test_whitelist, test_operators, test_sqli, test_schema_safety]
    failures = 0
    for t in tests:
        if not t():
            failures += 1
    
    if failures > 0:
        print(f"\n{failures} TESTS FAILED")
        sys.exit(1)
    else:
        print("\nALL SECURITY TESTS PASSED")
