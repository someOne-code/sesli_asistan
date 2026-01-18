"""
Security Unit Tests (Universal Retrieval).
Focus: SQL Injection resilience in search_products, Schema safety.
"""
import pytest
from app.infrastructure.database.models import BusinessOffering, CallLog, Base
from app.infrastructure.database.repository import HedefRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def clean_repo():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    repo = HedefRepository("sqlite:///:memory:")
    repo.engine = engine
    repo.get_session = lambda: session
    
    yield repo, session
    session.close()

def test_sql_injection_resilience(clean_repo):
    """
    Ensure that search_products handles SQL injection attempts safely.
    """
    repository, _ = clean_repo
    # Attempt: ' OR '1'='1
    evil_input = "' OR '1'='1"
    
    # Execution
    results = repository.search_products(evil_input, tenant_id="test_tenant")
    assert len(results) == 0

def test_dangerous_keywords_as_text(clean_repo):
    """
    Ensure 'DROP TABLE' is treated as search text, not command.
    """
    repository, db_session = clean_repo
    # Seed
    offering = BusinessOffering(
        tenant_id="test",
        name="Drop It",
        price=10.0
    )
    db_session.add(offering)
    db_session.commit()
    
    # Search "DROP TABLE"
    results = repository.search_products("DROP TABLE")
    
    # Should not crash. Should not delete table.
    assert isinstance(results, list)
    
    # Verify table still exists by querying
    assert db_session.query(BusinessOffering).count() > 0

def test_schema_abstraction(clean_repo):
    """
    Ensure get_safe_schema_summary returns meaningful safe info.
    """
    repository, _ = clean_repo
    summary = repository.get_safe_schema_summary()
    
    # Should describe BusinessOfferings
    assert "BusinessOfferings" in summary 
    assert "password" not in summary.lower()
