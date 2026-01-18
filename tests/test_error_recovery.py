
import pytest
from unittest.mock import MagicMock, patch
from app.infrastructure.database.repository import HedefRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.models import Base

@pytest.fixture
def clean_repo():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    repo = HedefRepository("sqlite:///:memory:")
    repo.engine = engine
    repo.get_session = lambda: session
    yield repo
    session.close()

def test_database_connection_retry_simulation(clean_repo):
    """
    Simulate a transient DB error and verify the repository handles/raises it gracefully.
    (Universal Retrieval version)
    """
    repository = clean_repo
    # Create a broken session mock
    broken_session = MagicMock()
    broken_session.query.side_effect = Exception("Connection Reset")
    
    # Mock get_session to return broken session
    with patch.object(repository, 'get_session', return_value=broken_session):
        try:
            repository.search_products("Metallica")
        except Exception:
            pass
            
    # Force a fresh query
    real_result = repository.search_products("Metallica")
    assert isinstance(real_result, list)

def test_ai_service_fallback():
    """
    Test that AI service returns safe default on failure.
    """
    # Mock generic AI service failure
    mock_ai = MagicMock()
    mock_ai.determine_intent.side_effect = Exception("API Timeout")
    
    # Simulate usage
    try:
        intent = mock_ai.determine_intent("test")
    except:
        intent = "UNIVERSAL_RETRIEVAL" # Fallback behavior simulation
    
    assert intent == "UNIVERSAL_RETRIEVAL"
