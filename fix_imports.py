import os

def fix_files():
    # Bu dosyalarda eski import kalmış olabilir, düzeltiyoruz.
    files_to_check = [
        "tests/test_api_e2e.py",
        "scripts/debug_integration_tests.py",
        "scripts/debug_benchmark.py",
        "scripts/auto_verify_ai.py",
        "app/main.py"
    ]
    
    # Also verify tests directory broadly if needed, but sticking to list first
    
    print("🔧 Import Düzeltme İşlemi Başlatılıyor...")

    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"⚠️ Dosya bulunamadı: {file_path}")
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Hatalı: from app.services.assistant_service import AssistantService
        # Doğru:  from app.core.services.assistant_service import AssistantService
        
        corrected_import = "from app.core.services.assistant_service import AssistantService"
        
        new_content = content.replace(
            "from app.services.assistant_service import AssistantService",
            corrected_import
        )
        
        # Also handle potential direct module usage if present (less likely for class import)
        
        if content != new_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ Düzeltildi: {file_path}")
        else:
            # Check if it was already correct or didn't need it
            if corrected_import in content:
                 print(f"👍 Zaten doğru: {file_path}")
            else:
                 print(f"ℹ️ Değişiklik yok (Eski import bulunamadı): {file_path}")

if __name__ == "__main__":
    fix_files()
