import requests
import json
import time

BASE_URL = "http://localhost:8000"
TENANT_ID = "berber_ahmet"

def send_message(text):
    print(f"\n🗣️  Kullanıcı: {text}")
    try:
        start = time.time()
        # API expects tenant_id in headers or context logic.
        # Based on logs, it might be resolving tenant via prompt headers?
        # Let's assume the endpoint handles context or we use a header.
        # Looking at previous logs, we might just use POST /process_audio or similar?
        # Actually, let's use the 'test_logic.py' style but against localhost.
        
        # But wait, looking at uvicorn setup, main:app is likely a Gateway.
        # Let's try sending a simple POST request assuming a standard schema.
        
        payload = {"user_text": text, "tenant_id": TENANT_ID} # Typical guesswork
        headers = {"Content-Type": "application/json"}
        
        # Use the new Text-Only Debug Endpoint
        payload = {
            "user_text": text, 
            "tenant_id": TENANT_ID
        }
        
        response = requests.post(f"{BASE_URL}/debug/chat", json=payload, headers=headers)
        end = time.time()
        
        if response.status_code == 200:
            data = response.json()
            # Try to find the answer key
            ans = data.get("ai_response") or data.get("response") or str(data)
            debug_info = data.get("debug_tenant", "MISSING")
            print(f"🤖 Asistan ({end-start:.2f}s) [Tenant: {debug_info}]: {ans}")
        else:
             print(f"❌ Hata: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")

if __name__ == "__main__":
    print(f"🚀 CANLI TEST BAŞLIYOR: {TENANT_ID}")
    time.sleep(1)
    
    # 1. Normal İstek
    send_message("Merhaba, saç kesimi ne kadar?")
    
    # 2. Randevu İsteği
    send_message("Yarın saat 14:00 uygun mu?")
    
    # 3. Alakasız İstek
    send_message("Hava durumu nasıl?")
