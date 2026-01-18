# tablo_listesi.py
import sqlite3

conn = sqlite3.connect('hedef.db')
cursor = conn.cursor()

# Tüm tabloları listele
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=== TABLOLAR ===")
for table in tables:
    table_name = table[0]
    print(f"\nTable: {table_name}")
    
    # Her tablonun sütunlarını göster
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    for col in columns:
        col_id, name, col_type, notnull, default, pk = col
        print(f"  - {name} ({col_type})" + (" [PRIMARY KEY]" if pk else ""))
    
    # Foreign key'leri göster
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    fks = cursor.fetchall()
    if fks:
        print("  Foreign Keys:")
        for fk in fks:
            print(f"    - {fk[3]} → {fk[2]}.{fk[4]}")

conn.close()