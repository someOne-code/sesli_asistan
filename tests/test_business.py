"""
Unit Tests for Repository Business Logic (SaaS Architecture).
Checks BusinessOffering search, sorting, and tenant isolation.
"""
import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.models import BusinessOffering, Base
from app.infrastructure.database.repository import HedefRepository

@pytest.fixture
def clean_repo():
    # 1. Setup In-Memory DB (SQLite)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 2. Setup Repo
    repo = HedefRepository("sqlite:///:memory:")
    repo.engine = engine
    repo.get_session = lambda: session
    
    # 3. Yield
    yield repo, session
    
    # 4. Cleanup
    session.close()

def test_search_products_basic(clean_repo):
    """Test basic keyword search functionality within BusinessOffering."""
    repository, db_session = clean_repo
    
    # Seed
    offering = BusinessOffering(
        tenant_id="test_tenant",
        name="BatteryTest",
        category="Metal",
        price=10.0,
        description="Metallica Song"
    )
    db_session.add(offering)
    db_session.commit()
    
    # Act
    products = repository.search_products("Battery", tenant_id="test_tenant")
    
    # Assert
    assert len(products) == 1
    assert products[0].name == "BatteryTest"
    assert "Metal" in products[0].description

def test_search_products_sorting(clean_repo):
    """Test filters={"sort": "price_desc"}."""
    repository, db_session = clean_repo
    
    # Seed
    t1 = BusinessOffering(tenant_id="t1", name="ItemCheap", price=5.0)
    t2 = BusinessOffering(tenant_id="t1", name="ItemExpensive", price=50.0)
    db_session.add_all([t1, t2])
    db_session.commit()
    
    # Act
    # Pass tenant_id to respect isolation
    products = repository.search_products("Item", filters={"sort": "price_asc"}, tenant_id="t1")
    
    # Assert
    assert len(products) > 0
    assert products[0].name == "ItemCheap"

def test_search_products_tenant_isolation(clean_repo):
    """
    CRITICAL SAAS TEST: 
    Verify that querying for tenant A does not return tenant B's products.
    """
    repository, db_session = clean_repo
    
    # Seed Tenant A (Berber)
    db_session.add(BusinessOffering(tenant_id="berber", name="Saç Kesimi", price=100))
    
    # Seed Tenant B (Music)
    db_session.add(BusinessOffering(tenant_id="music", name="Metallica CD", price=20))
    
    db_session.commit()
    
    # Act 1: Search for Berber
    results_berber = repository.search_products(query=None, tenant_id="berber")
    assert len(results_berber) == 1
    assert results_berber[0].name == "Saç Kesimi"
    
    # Act 2: Search for Music
    results_music = repository.search_products(query=None, tenant_id="music")
    assert len(results_music) == 1
    assert results_music[0].name == "Metallica CD"
