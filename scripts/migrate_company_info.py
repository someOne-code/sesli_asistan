# -*- coding: utf-8 -*-
"""
Company Knowledge Base Migration
==================================
Creates multi-tenant company_info table with seed data.

CRITICAL: This is a MULTI-TENANT table.
Each tenant has isolated data.
"""

import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "hedef.db")


def migrate():
    """Create company_info table with tenant isolation."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[MIGRATION] Creating company_info table...")
    
    # Create table with tenant isolation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            topic_key TEXT NOT NULL,
            content TEXT NOT NULL,
            locale TEXT DEFAULT 'tr',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tenant_id, topic_key, locale)
        )
    """)
    
    print("[MIGRATION] Table created successfully.")
    
    # Seed data for Chinook Music Store (tenant: chinook_music)
    print("[MIGRATION] Seeding data for tenant: chinook_music...")
    
    seed_data = [
        # Vizyon
        (
            "chinook_music",
            "vizyon",
            "Vizyonumuz, yapay zeka teknolojilerini her işletmenin ulaşabileceği basitlikte sunarak, müşteri iletişimini kusursuz hale getirmektir. Müzik endüstrisinde dijital dönüşümün öncüsü olmayı hedefliyoruz.",
            "tr"
        ),
        # Misyon
        (
            "chinook_music",
            "misyon",
            "Misyonumuz, müzik severlere en kaliteli albüm ve şarkıları en uygun fiyatlarla sunmak, sanatçıları desteklemek ve müzik kültürünü yaygınlaştırmaktır.",
            "tr"
        ),
        # Adres
        (
            "chinook_music",
            "adres",
            "Chinook Music Store - Teknopark İstanbul, B Blok, No:12, Pendik/İstanbul, Türkiye",
            "tr"
        ),
        # İletişim
        (
            "chinook_music",
            "iletisim",
            "Bize 0850 123 45 67 numarasından veya info@chinookmusic.com adresinden ulaşabilirsiniz. Müşteri hizmetlerimiz Pazartesi-Cuma 09:00-18:00 saatleri arasında hizmetinizdedir.",
            "tr"
        ),
        # Hakkında
        (
            "chinook_music",
            "hakkinda",
            "Chinook Music Store, 2010 yılından beri müzik severlere hizmet veren, Türkiye'nin önde gelen dijital müzik platformlarından biridir. Rock, Jazz, Blues, Metal ve daha birçok türde binlerce albüm ve şarkıya sahibiz.",
            "tr"
        ),
    ]
    
    cursor.executemany(
        """
        INSERT OR IGNORE INTO company_info (tenant_id, topic_key, content, locale)
        VALUES (?, ?, ?, ?)
        """,
        seed_data
    )
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM company_info WHERE tenant_id = 'chinook_music'")
    count = cursor.fetchone()[0]
    print(f"[MIGRATION] Seeded {count} records for chinook_music")
    
    # Show sample data
    print("\n[MIGRATION] Sample data:")
    cursor.execute("""
        SELECT topic_key, content 
        FROM company_info 
        WHERE tenant_id = 'chinook_music' 
        LIMIT 3
    """)
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1][:50]}...")
    
    conn.close()
    print("\n[MIGRATION] ✅ Migration completed successfully!")


if __name__ == "__main__":
    migrate()
