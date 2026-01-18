from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.database.models import CallLog

repo = HedefRepository('sqlite:///hedef.db')
session = repo.get_session()

logs = session.query(CallLog).order_by(CallLog.timestamp.desc()).limit(10).all()

print("=" * 80)
print("SON 10 KONUSMA KAYDI")
print("=" * 80)

for i, log in enumerate(logs, 1):
    print(f"\nKayit #{i}")
    print(f"Zaman: {log.timestamp}")
    print(f"Kullanici: {log.customer_text}")
    print(f"Melody: {log.ai_response}")
    print(f"Duygu: {log.sentiment}")
    if log.intent:
        print(f"Intent: {log.intent}")
    print("-" * 80)

session.close()
