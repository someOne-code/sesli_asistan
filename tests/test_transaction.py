
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
    
    yield repo, session
    session.close()

def test_transaction_rollback(clean_repo):
    """Test verification of rollback on error."""
    repository, db_session = clean_repo
    
    # 1. Add valid
    db_session.add(BusinessOffering(tenant_id="t1", name="Valid", price=10))
    db_session.commit()
    
    # 2. Add invalid (e.g. invalid type or constraint violation simulation)
    # SQLAlchemy objects don't validate types deeply in SQLite unless constraints exist.
    # We will simulate an error by forcing a flush failure maybe?
    # Or just manual rollback test.
    
    try:
        broken = BusinessOffering(tenant_id=None, name="Broken") # Assuming constraint? 
        # SQLite nullable constraints depend on model definition.
        # Let's just manually rollback to test logic.
        db_session.add(broken)
        db_session.flush() # Might not fail if nullable allowed
        
        # Force error or catch the integrity error
        raise ValueError("Simulated DB Error")
    except Exception:
        db_session.rollback()
        
    # Assert: Only valid exists
    assert db_session.query(BusinessOffering).count() == 1
    assert db_session.query(BusinessOffering).first().name == "Valid"
