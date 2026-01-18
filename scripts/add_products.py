import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.infrastructure.database.engine_manager import get_session_factory
from app.infrastructure.database.models import BusinessOffering, Tenant

def add_demo_products():
    session_factory = get_session_factory(settings.DB_NAME)
    with session_factory() as session:
        try:
            tenant_id = "berber_ahmet"
            
            # 1. Clear existing products for this tenant (to avoid duplicates)
            session.query(BusinessOffering).filter_by(tenant_id=tenant_id).delete()
            
            # 2. Add Products
            products = [
                BusinessOffering(
                    tenant_id=tenant_id,
                    name="Saç Kesimi",
                    price=250.0,
                    currency="TL",
                    description="Modern saç kesimi ve yıkama dahil."
                ),
                BusinessOffering(
                    tenant_id=tenant_id,
                    name="Sakal Tıraşı",
                    price=150.0,
                    currency="TL",
                    description="Geleneksel ustura veya makine ile sakal tıraşı."
                ),
                BusinessOffering(
                    tenant_id=tenant_id,
                    name="Saç Yıkama",
                    price=50.0,
                    currency="TL",
                    description="Fönlü saç yıkama ve bakım."
                ),
                BusinessOffering(
                    tenant_id=tenant_id,
                    name="Damat Tıraşı",
                    price=1500.0,
                    currency="TL",
                    description="Özel gün için VIP bakım paketi."
                )
            ]
            
            session.add_all(products)
            session.commit()
            print(f"✅ {len(products)} adet ürün '{tenant_id}' için eklendi.")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Hata: {e}")

if __name__ == "__main__":
    add_demo_products()
