
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.infrastructure.database.models import Base, CallLog

def inspect_logs():
    db_path = "hedef.db"
    if not os.path.exists(db_path):
        if os.path.exists("chinook.db"):
             db_path = "chinook.db"

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    print(f"\nSearching for latest 'Metallica' log in {db_path}...")
    try:
        # Find last Metallica log
        log = session.query(CallLog).filter(CallLog.customer_text.ilike('%Metallica%')).order_by(CallLog.timestamp.desc()).first()
        
        if log:
            print(f"\n✅ FOUND METALLICA LOG:")
            print(f"ID: {log.id}")
            print(f"Time: {log.timestamp}")
            print(f"Text: {log.customer_text}")
            print(f"Intent: {log.intent}  <-- CHECK THIS")
            print(f"Response: {log.ai_response[:50]}...")
        else:
            print("❌ No 'Metallica' log found.")

        print("-" * 60)
        print("Last 3 Logs:")
        logs = session.query(CallLog).order_by(CallLog.timestamp.desc()).limit(3).all()
        for l in logs:
             print(f"[{l.id}] {l.customer_text} -> Intent: {l.intent}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_logs()
