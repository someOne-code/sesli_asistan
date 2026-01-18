import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.infrastructure.database.engine_manager import get_session_factory
from app.infrastructure.database.models import BusinessOffering

def verify_products():
    print("🔍 Ürün Doğrulama Başlıyor...")
    session_factory = get_session_factory(settings.DB_NAME)
    with session_factory() as session:
        try:
            tenant_id = "berber_ahmet"
            products = session.query(BusinessOffering).filter_by(tenant_id=tenant_id).all()
            
            if not products:
                print(f"❌ '{tenant_id}' için hiç ürün BULUNAMADI!")
            else:
                print(f"✅ '{tenant_id}' için {len(products)} ürün bulundu:")
                for p in products:
                    print(f" - {p.name} ({p.price} {p.currency})")
                    
        except Exception as e:
            print(f"❌ Veritabanı Hatası: {e}")

if __name__ == "__main__":
    verify_products()
