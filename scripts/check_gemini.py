import os
import google.generativeai as genai

# .env dosyasından manuel okuma (dependency sorunu olmaması için)
api_key = None
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.strip().startswith("GEMINI_API_KEY="):
                # Eşittirden sonrasını al ve varsa tırnakları temizle
                parts = line.strip().split("=", 1)
                if len(parts) > 1:
                    api_key = parts[1].strip().strip('"').strip("'")
                break

if not api_key:
    print("HATA: .env dosyasında GEMINI_API_KEY bulunamadı!")
else:
    print(f"API Anahtarı bulundu: {api_key[:5]}...{api_key[-3:]}")
    print("Modeller listeleniyor, lütfen bekleyin...\n")
    
    try:
        genai.configure(api_key=api_key)
        
        with open("models_result.txt", "w", encoding="utf-8") as f:
            f.write("--- KULLANILABİLİR MODELLER ---\n")
            found = False
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    f.write(f"MODEL: {m.name} ({m.display_name})\n")
                    print(f"BULUNDU: {m.name}") # Console feedback
                    found = True
            
            if not found:
                f.write("UYARI: Hiçbir model bulunamadı.\n")
                
    except Exception as e:
        print(f"HATA: {e}")
        with open("models_result.txt", "w", encoding="utf-8") as f:
            f.write(f"HATA: {e}")
