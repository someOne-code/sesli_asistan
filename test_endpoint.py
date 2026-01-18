import requests

# Test 1: API'ye basit bir istek at
response = requests.get("http://localhost:8000/")
print(f"Homepage Status: {response.status_code}")

# Test 2: /talk endpoint'ine dummy ses gönder
import io

# Boş bir audio dosyası oluştur
dummy_audio = io.BytesIO(b"dummy audio data")
dummy_audio.name = "test.webm"

files = {'file': ('test.webm', dummy_audio, 'audio/webm')}
data = {'session_id': 'test_session'}

try:
    response = requests.post("http://localhost:8000/talk", files=files, data=data, timeout=10)
    print(f"\n/talk Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response Size: {len(response.content)} bytes")
    
    # İlk 100 byte'ı göster
    print(f"First 100 bytes: {response.content[:100]}")
    
except Exception as e:
    print(f"Error: {e}")
