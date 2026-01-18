
import pytest
from app.infrastructure.database.models import BusinessOffering, Base
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
    yield repo
    session.close()

def test_unicode_handling(clean_repo):
    """Unicode karakterler doğru işleniyor mu?"""
    repository = clean_repo
    unicode_inputs = [
        "Müzik",  # Turkish
        "音楽",   # Japanese
        "🎵🎶",   # Emoji
        "Москва", # Cyrillic
    ]
    
    for text in unicode_inputs:
        result = repository.search_products(text, tenant_id="test_tenant")
        assert isinstance(result, list)

def test_empty_database(clean_repo):
    """Boş veritabanında ne olur?"""
    repository = clean_repo
    result = repository.search_products("NON_EXISTENT_IMPOSSIBLE_STRING_XYZ", tenant_id="test_tenant")
    assert result == []

def test_large_input_string(clean_repo):
    """Çok uzun input"""
    repository = clean_repo
    long_text = "A" * 5000
    try:
        result = repository.search_products(long_text, tenant_id="test_tenant")
        assert isinstance(result, list)
    except Exception as e:
        pytest.fail(f"Large input crashed the app: {e}")
