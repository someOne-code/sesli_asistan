
import sys
import os

sys.path.append(os.getcwd())

try:
    print("Attempting to import Base...")
    from app.infrastructure.database.models import Base
    print("Import successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
