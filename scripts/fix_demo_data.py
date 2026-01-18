
from app.infrastructure.database.engine_manager import get_session_factory
from app.core.config import settings
from app.infrastructure.database.models import BusinessOffering

def fix_data():
    print("🔧 Fixing Demo Data for 'berber_ahmet'...")
    db_url = f"sqlite:///{settings.DB_NAME}"
    factory = get_session_factory(db_url)
    session = factory()
    
    try:
        # Update category for Berber Ahmet products
        products = session.query(BusinessOffering).filter_by(tenant_id="berber_ahmet").all()
        count = 0
        for p in products:
            if not p.category:
                p.category = "Erkek Bakım"
                count += 1
        
        session.commit()
        print(f"✅ Updated {count} products with category 'Erkek Bakım'.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_data()
