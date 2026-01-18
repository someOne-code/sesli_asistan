import pytest
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database.engine_manager import (
    get_engine, 
    get_session_factory, 
    dispose_all_engines,
    _ENGINE_CACHE
)

# Fixture to clear engines before/after tests
@pytest.fixture(autouse=True)
def clean_engines():
    dispose_all_engines()
    yield
    dispose_all_engines()

def test_engine_singleton():
    """Same URL should return same engine instance"""
    url = "sqlite:///test_singleton.db" # Avoid :memory: for clarity
    engine1 = get_engine(url)
    engine2 = get_engine(url)
    
    # We verify identity
    assert engine1 is engine2, f"Engines are not identical! IDs: {id(engine1)} vs {id(engine2)}"

def test_session_factory_singleton():
    url = "sqlite:///test_factory.db"
    f1 = get_session_factory(url)
    f2 = get_session_factory(url)
    assert f1 is f2

def test_different_urls():
    e1 = get_engine("sqlite:///db1.db")
    e2 = get_engine("sqlite:///db2.db")
    assert e1 is not e2
