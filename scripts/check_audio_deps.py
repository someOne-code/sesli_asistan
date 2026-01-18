import sys

print(f"Python Executable: {sys.executable}")
print("-" * 20)

packages = ["speech_recognition", "pygame", "edge_tts", "pyaudio"]

for pkg in packages:
    try:
        if pkg == "speech_recognition":
            import speech_recognition
        elif pkg == "pygame":
            import pygame
        elif pkg == "edge_tts":
            import edge_tts
        elif pkg == "pyaudio":
            import pyaudio
            
        print(f"✅ {pkg} FOUND")
    except ImportError as e:
        print(f"❌ {pkg} MISSING ({e})")
    except Exception as e:
        print(f"❌ {pkg} ERROR ({e})")
