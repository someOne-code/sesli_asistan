import sqlite3

# DB dosyanın yolu
db_path = r"C:\Users\umut\OneDrive\Masaüstü\jules_session_11343452395066098440\hedef.db"


# Bağlan
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabloları al
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

schema_info = ""

for table_name_tuple in tables:
    table_name = table_name_tuple[0]
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()  # (cid, name, type, notnull, dflt_value, pk)
    
    schema_info += f"Table {table_name}:\n"
    for col in columns:
        col_name, col_type = col[1], col[2]
        schema_info += f"  - {col_name} ({col_type})\n"
    schema_info += "\n"

conn.close()

print(schema_info)
