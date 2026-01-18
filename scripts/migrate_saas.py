"""
SaaS Migration Script (Absolutely Safe Mode)
============================================
Migrates legacy Chinook data to BusinessOffering schema.
Uses HARDCODED PATHS to avoid environment issues.
"""
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Hardcoded absolute path for reliability
BASE_DIR = r"c:\Users\umut\OneDrive\Masaüstü\sesli asistan"
sys.path.append(BASE_DIR)

# Manually Import Models to avoid import errors if app structure is weird
# We rely on the app structure being correct relative to sys.path
try:
    from app.infrastructure.database.models import Base, BusinessOffering, CompanyInfo, Tenant
except ImportError:
    # Fallback if python path fails
    sys.path.append(os.path.join(BASE_DIR, "app"))
    from app.infrastructure.database.models import Base, BusinessOffering, CompanyInfo, Tenant

def migrate():
    # Database URL with absolute path
    db_path = os.path.join(BASE_DIR, "hedef.db")
    db_url = f"sqlite:///{db_path}"
    
    print(f"🚀 Connecting to Database: {db_url}")
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 2. Check Legacy Tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"DEBUG: Found tables: {tables}")
        
        has_legacy = all(t in tables for t in ['Track', 'Album', 'Genre', 'Artist'])
        
        # 3. Create New Tables
        Base.metadata.create_all(bind=engine)
        print("✅ Schema checked/updated.")
        
        # 4. Migrate Chinook
        if has_legacy:
            existing = session.query(BusinessOffering).filter_by(tenant_id='chinook').first()
            if not existing:
                print("🔄 Migrating Chinook Music Data...")
                legacy_sql = text("""
                    SELECT t.Name as TrackName, a.Title as AlbumTitle, g.Name as GenreName, ar.Name as ArtistName, t.UnitPrice
                    FROM Track t
                    JOIN Album a ON t.AlbumId = a.AlbumId
                    JOIN Genre g ON t.GenreId = g.GenreId
                    JOIN Artist ar ON a.ArtistId = ar.ArtistId
                """)
                legacy_rows = session.execute(legacy_sql).fetchall()
                
                offerings = []
                for row in legacy_rows:
                    full_name = f"{row.ArtistName} - {row.TrackName}"
                    offerings.append(BusinessOffering(
                        tenant_id='chinook',
                        name=full_name,
                        category=row.GenreName,
                        description=f"Album: {row.AlbumTitle}",
                        price=row.UnitPrice,
                        currency="USD",
                        is_active=True
                    ))
                session.bulk_save_objects(offerings)
                
                # Tenant
                chinook = session.query(Tenant).filter_by(id='chinook').first()
                if not chinook:
                    session.add(Tenant(id='chinook', name='Chinook Music Store'))
                    
                print(f"✅ Migrated {len(offerings)} tracks.")
            else:
                print("ℹ️ Chinook data already migrated.")
        else:
            print("⚠️ Legacy tables not found.")

        # 5. Seed Berber Ahmet
        berber = session.query(Tenant).filter_by(id='berber_ahmet').first()
        # Always update Berber Ahmet for demo consistency
        if True:
            print("✂️ Updating 'Berber Ahmet'...")
            if not berber:
                berber = Tenant(id='berber_ahmet', name='Berber Ahmet Efendi')
                session.add(berber)
            
            # Clear old company info for this tenant
            session.execute(text("DELETE FROM company_info WHERE tenant_id = 'berber_ahmet'"))
            
            info_data = [
                ("vizyon", "Vizyonumuz: Geleneksel mahalle berberliğini modern dokunuşlarla birleştirerek, her erkeğin kendini özel hissettiği bir bakım deneyimi sunmak."),
                ("misyon", "Misyonumuz: Hijyenik ortamda, kaliteli sohbet eşliğinde en iyi saç ve sakal bakımını uygun fiyatlarla sunmak."),
                ("adres", "Bursa Nilüfer, FSM Bulvarı No:16 (Starbucks yanı)"),
                ("telefon", "0532 123 45 67"),
                ("email", "ahmet@berberahmet.com"),
                ("saatler", "Hafta içi 09:00 - 20:00, Cumartesi 10:00 - 18:00, Pazar kapalı."),
                ("randevu", "Randevularınızı telefonla veya web sitemizden alabilirsiniz.")
            ]
            for k, v in info_data:
                session.add(CompanyInfo(tenant_id='berber_ahmet', topic_key=k, content=v))
                
            # Clear offerings
            session.execute(text("DELETE FROM business_offerings WHERE tenant_id = 'berber_ahmet'"))
            
            services = [
                ("Saç Kesimi", "Hizmet", 250.0, "Modern makas ve makine teknikleriyle profesyonel kesim."),
                ("Sakal Kesimi", "Hizmet", 150.0, "Sıcak havlu kompresli lüks sakal tıraşı."),
                ("Saç Yıkama & Fön", "Hizmet", 100.0, "Rahatlatıcı masaj, yıkama ve fön çekimi."),
                ("Damat Tıraşı", "Paket", 1500.0, "Özel gününüz için saç, sakal, cilt bakımı ve maske paketi."),
                ("Çocuk Tıraşı", "Hizmet", 200.0, "Çocuklar için özel koltuk ve tabletli kesim.")
            ]
            for n, c, p, d in services:
                session.add(BusinessOffering(
                    tenant_id='berber_ahmet',
                    name=n,
                    category=c,
                    price=p,
                    description=d,
                    currency="TRY"
                ))
            print("✅ Berber Ahmet updated.")
            
        session.commit()
        print("🎉 MIGRATION SUCCESSFUL!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
