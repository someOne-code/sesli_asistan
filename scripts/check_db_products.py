
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.infrastructure.database.engine_manager import get_session_factory
from app.core.config import settings
from app.infrastructure.database.models import BusinessOffering

def check_products():
    db_url = f"sqlite:///{settings.DB_NAME}"
    print(f"Connecting to DB: {db_url}")
    factory = get_session_factory(db_url)
    session = factory()
    
    try:
        products = session.query(BusinessOffering).all()
        print(f"\nTotal Products: {len(products)}")
        print("="*80)
        print(f"{'TENANT':<20} | {'PRODUCT':<30} | {'PRICE':<10} | {'CATEGORY'}")
        print("-" * 80)
        
        for p in products:
            price_display = f"{p.price} {p.currency}"
            print(f"{p.tenant_id:<20} | {p.name:<30} | {price_display:<10} | {p.category}")
            
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_products()
