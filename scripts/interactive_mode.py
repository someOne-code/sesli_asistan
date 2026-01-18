import asyncio
import sys
import os
import shutil
import random
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database.repository import HedefRepository
from app.infrastructure.ai.groq_service import GroqAIService
from app.core.services.assistant_service import AssistantService
from app.infrastructure.text.rule_based_normalizer import RuleBasedNormalizer
from app.core.config import settings

# Voice Libs
try:
    import speech_recognition as sr
    import pygame
    import edge_tts
    VOICE_AVAILABLE = True
except Exception as e:
    VOICE_AVAILABLE = False
    print(f"⚠️ Ses kütüphaneleri yüklenemedi: {e}")
    print("Sadece metin modu çalışacak.")

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"

async def play_audio(text: str):
    if not VOICE_AVAILABLE or not text:
        return

    try:
        # Generate Audio
        voice = settings.SES_MODELI or "tr-TR-AhmetNeural"
        output_file = f"temp_output_{int(time.time())}.mp3"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)

        # Play Audio
        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
            
        pygame.mixer.quit()
        
        # Cleanup
        try:
            os.remove(output_file)
        except:
            pass
            
    except Exception as e:
        print(f"{RED}[TTS Error] Ses oynatılamadı: {e}{RESET}")

def listen_mic():
    if not VOICE_AVAILABLE:
        return None
        
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print(f"{RED}🎙️  Dinliyorum... (Konuşun){RESET}")
        try:
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            print(f"{YELLOW}⏳ İşleniyor...{RESET}")
            text = r.recognize_google(audio, language="tr-TR")
            return text
        except sr.WaitTimeoutError:
            print(f"{RED}❌ Zaman aşımı. Ses gelmedi.{RESET}")
            return None
        except sr.UnknownValueError:
            print(f"{RED}❌ Anlaşılamadı.{RESET}")
            return None
        except Exception as e:
            print(f"{RED}❌ Hata: {str(e)}{RESET}")
            return None

async def main():
    # 1. Init System
    print(f"{GREEN}>>> MELODY SESLİ ASİSTAN (VOICE EDITION) BAŞLATILIYOR...{RESET}")
    print("Veritabanı bağlanıyor...")
    
    repo = HedefRepository("hedef.db")
    ai = GroqAIService(api_key=settings.GROQ_API_KEY)
    normalizer = RuleBasedNormalizer()
    service = AssistantService(db_repo=repo, ai_service=ai, normalizer=normalizer)
    
    print(f"{GREEN}>>> SİSTEM HAZIR! TELEFON MODU AKTİF 📞{RESET}")
    print(f"{YELLOW}>>> Sizi sürekli dinliyorum. Konuşmaya başlayın.{RESET}")
    print(f"{YELLOW}>>> Sessiz kalırsanız yazma moduna geçer.{RESET}\n")
    
    # 2. Conversation Loop with Memory
    history = [] 
    
    while True:
        try:
            # prompt_text = ... (Removed for auto-listen)
            # user_input = ... (Removed)
            
            # Voice Mode Trigger - AUTO LISTEN
            if VOICE_AVAILABLE:
                recognized = listen_mic()
                if recognized:
                    user_input = recognized
                    print(f"\n{CYAN}Siz (Ses): {user_input}{RESET}")
                else:
                    # If silence or error, ask for text
                    print(f"\n{YELLOW}Ses anlaşılamadı veya sessizlik. Yazmak ister misiniz? (Enter basıp geçebilirsiniz){RESET}")
                    user_input = input(f"{CYAN}Siz (Yazı): {RESET}").strip()
            else:
                 user_input = input(f"{CYAN}Siz (Yazı): {RESET}").strip()

            if not user_input:
                continue
                
            if user_input.lower() in ["q", "exit", "çıkış", "kapat"]:
                print("Görüşürüz! 👋")
                await play_audio("Görüşürüz, kendine iyi bak.")
                break
                
            # Formatting history 
            context_str = "\n".join(history[-6:]) 
            
            # Process
            print(f"{YELLOW}Melody düşünüyor...{RESET}", end="\r")
            
            result = await service.process_user_input(
                user_input, 
                conversation_history=context_str
            )
            
            ai_response = result["ai_response"]
            
            # Clear loading line
            print(" " * 50, end="\r")
            print(f"{GREEN}Melody: {ai_response}{RESET}")
            
            # Async Play Audio (Fire and wait, or background?)
            # User wants to hear it. Wait is better natural flow.
            await play_audio(ai_response)
            
            # Update Memory
            history.append(f"User: {user_input}")
            history.append(f"AI: {ai_response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n{YELLOW}Hata: {e}{RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
