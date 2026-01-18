import sqlite3

def view_logs():
    try:
        conn = sqlite3.connect('hedef.db')
        cursor = conn.cursor()
        
        print("\n--- SON 5 KONUŞMA KAYDI (ÖZET KONTROLÜ) ---\n")
        
        cursor.execute("SELECT id, summary, customer_text, ai_response FROM call_logs ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        
        if not rows:
            print("Kayıt bulunamadı.")
        
        for row in rows:
            log_id, summary, user, ai = row
            print(f"ID: {log_id}")
            print(f"User: {user}")
            print(f"AI: {ai[:50]}...")
            print(f"SUMMARY: {summary}")
            print("-" * 30)
            
        conn.close()
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    view_logs()
