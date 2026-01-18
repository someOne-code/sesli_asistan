import os

def fix_imports():
    targets = [
        "scripts/simulate_user_scenario.py",
        "scripts/test_logic.py",
        "scripts/test_low_latency.py",
        "scripts/test_streaming.py"
    ]
    
    print("🔧 Fixing Final Zombie Imports...")
    
    for filepath in targets:
        if not os.path.exists(filepath):
            print(f"⚠️ Not found: {filepath}")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Replace legacy service import
        new_content = content.replace(
            "from app.services.assistant_service",
            "from app.core.services.assistant_service"
        )
        # Also catch the direct class import if phrased differently but similarly
        new_content = new_content.replace(
            "import app.services.assistant_service",
            "import app.core.services.assistant_service"
        )

        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ Fixed: {filepath}")
        else:
            print(f"👍 No changes needed: {filepath}")

if __name__ == "__main__":
    fix_imports()
