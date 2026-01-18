
import sys
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.infrastructure.database.models import Base, CallLog
from app.infrastructure.database.repository import SqliteMusicRepository

def interactive_uat():
    print("\n" + "="*60)
    print("🎭 INTERACTIVE UAT (User Acceptance Testing) DIRECTOR")
    print("="*60)
    print("This script will guide you through testing the Voice Assistant.")
    print("Please have 'index.html' open in your browser.")
    print("-" * 60)
    
    # Setup DB Connection to READ REAL LOGS
    # Note: Config default is 'hedef.db'
    db_path = "hedef.db" 
    if not os.path.exists(db_path):
        print(f"WARNING: '{db_path}' not found. Using 'chinook.db' as fallback.")
        if os.path.exists("chinook.db"):
             db_path = "chinook.db"
    
    repo = SqliteMusicRepository(f"sqlite:///{db_path}")
    
    # ---------------------------------------------------------
    # SCENARIO 1: START CALL
    # ---------------------------------------------------------
    print("\n🎬 SCENARIO 1: Basic Call Flow")
    input("👉 ACTION: Click the Green 'Call' (📞) button in the browser.\n   Press ENTER here when done...")
    
    print("   Checking backend state... (Visual check only for client-side state)")
    print("   ✅ PASS: If you see '🎤 Dinliyorum...' and timer counting.")

    # ---------------------------------------------------------
    # SCENARIO 2: MUSIC INTENT
    # ---------------------------------------------------------
    print("\n🎬 SCENARIO 2: Music Intent")
    input("👉 ACTION: Say 'Metallica çal' clearly.\n   Wait for the audio response.\n   Press ENTER here after audio finishes...")
    
    print("   Verifying database logs (Scanning last 5 entries)...")
    found = False
    for attempt in range(3):
        try:
            session = repo.get_session()
            # Get last 5 logs to account for noise/silence/timing
            logs = session.query(CallLog).order_by(CallLog.timestamp.desc()).limit(5).all()
            
            for log in logs:
                text = (log.customer_text or "").lower()
                if "metallica" in text:
                    print(f"   ✅ PASS: Log found! Text: '{log.customer_text}' | Intent: '{log.intent}'")
                    found = True
                    break
            
            session.close()
            
            if found:
                break
                
            print(f"   ...Attempt {attempt+1}/3: Waiting for logs to flush...")
            time.sleep(2)
        except Exception as e:
            print(f"   ❌ ERROR reading DB: {e}")
            break

    if not found:
        print(f"   ⚠️ WARNING: 'Metallica' not found in recent logs.")
        print("   (Reason: Microphone level too low? Backend latnecy? Check backend console for '[TRANSCRIPTION]')")

    # ---------------------------------------------------------
    # SCENARIO 3: END CALL
    # ---------------------------------------------------------
    print("\n🎬 SCENARIO 3: End Call")
    input("👉 ACTION: Click the Red 'Hang Up' (❌) button.\n   Press ENTER here when done...")
    
    print("   ✅ PASS: If page reset/reloaded and 'Notlar kaydedildi' alert appeared.")
    
    print("\n" + "="*60)
    print("🎉 UAT SESSION COMPLETE")
    print(" Please mark the checklist in UAT_CHECKLIST.md based on your results.")
    print("="*60)

if __name__ == "__main__":
    interactive_uat()
