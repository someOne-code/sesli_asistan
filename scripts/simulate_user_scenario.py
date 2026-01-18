
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database.repository import HedefRepository
from app.core.services.assistant_service import AssistantService
from app.infrastructure.ai.groq_service import GroqAIService
from app.infrastructure.database.models import Artist, Album, Track, Genre

# Mock Data Seeder
def seed_if_needed(repo):
    session = repo.get_session()
    if session.query(Artist).filter_by(Name="Queen").first():
        session.close()
        return

    print("--- [MOCK DATA] Seeding 'Queen' data... ---")
    artist = Artist(Name="Queen")
    session.add(artist)
    session.commit()
    
    album = Album(Title="A Night at the Opera", ArtistId=artist.ArtistId)
    session.add(album)
    session.commit()
    
    genre = Genre(Name="Rock")
    session.add(genre)
    session.commit()
    
    track = Track(
        Name="Bohemian Rhapsody", 
        AlbumId=album.AlbumId, 
        GenreId=genre.GenreId, 
        Composer="Freddie Mercury", 
        UnitPrice=1.99
    )
    session.add(track)
    session.commit()
    session.close()

# Mock AI Service for Simulation
class MockAIService(GroqAIService):
    async def determine_intent(self, user_text: str) -> str:
        return "UNIVERSAL_RETRIEVAL"
        
    async def generate_response(self, user_text: str, context: str = None, conversation_history: str = "", is_first_message: bool = False) -> str:
        # Canned responses to demonstrate the persona
        if "Queen" in user_text:
            return "Veritabanımızda Queen grubundan 'A Night at the Opera' albümünden 'Bohemian Rhapsody' şarkısını buldum. Fiyatı 1.99 Dolar."
        
        if "pahalı" in user_text.lower():
            # In a real LLM, it would read the context. We simulate that.
            if context and "1.99" in str(context):
                return "Listemdeki en pahalı ürün 1.99 dolar fiyatıyla Bohemian Rhapsody."
            return "Şu an fiyat karşılaştırması yapamıyorum."
            
        if "satın almak" in user_text.lower() or "adresime" in user_text.lower():
             return "Üzgünüm, güvenlik kurallarım gereği telefondan sipariş alamıyorum veya ödeme işlemi yapamıyorum. Lütfen web sitemizi ziyaret edin."
             
        if "Tarkan" in user_text:
             if not context or "Bulunamadı" in str(context):
                 return "Maalesef kayıtlarımızda Tarkan ile ilgili bir ürün bulamadım."
             return "Tarkan bulundu."
             
        return "Size nasıl yardımcı olabilirim?"

async def run_simulation():
    print("--- 🎭 SİMÜLASYON BAŞLIYOR: 'ROCK MÜZİK KEŞFİ' SENARYOSU 🎭 ---")
    print("Amaç: Asistanın Universal Retrieval akışını ve Güvenlik Kurallarını göstermek.\n")

    # 1. Setup
    repo = HedefRepository("sqlite:///hedef.db")
    seed_if_needed(repo)
    
    # Use Mock AI
    ai_service = MockAIService(api_key="mock")
    service = AssistantService(repo, ai_service)
    
    session_id = "sim_user_002"
    history = ""
    
    turns = [
        ("Merhaba, Queen grubundan ne var elinizde?", "SEARCH (Context Retrieval)"),
        ("En pahalı şarkıları hangisi bunların?", "ANALYTICAL (Smart Sorting)"),
        ("Tamam süper, Bohemian Rhapsody'yi satın almak istiyorum, adresime yolla.", "ORDER (Security Refusal)"),
        ("Peki, Tarkan var mı?", "NEW SEARCH (Empty State)")
    ]
    
    is_first = True
    
    for user_text, note in turns:
        print(f"\n👤 KULLANICI: {user_text}")
        print(f"   [Senaryo Notu: {note}]")
        print("   🤖 Asistan düşünüyor...", end=" ", flush=True)
        
        # Real Pipeline Call
        try:
            result = await service.process_user_input(user_text, session_id, history, is_first_message=is_first)
            ai_response = result["ai_response"]
            context_used = result.get("context_used", "")
            
            print("✅")
            
            # Print Internal Reasoning (Context Found)
            if context_used:
                # Pretty print context snippet
                print(f"   🔎 [SİSTEM - BULUNAN ENTEGRASYON]: Veritabanından gelen veri:")
                lines = context_used.strip().split('\n')
                for line in lines[:3]: # Show first 3 lines
                    print(f"      -> {line}")
                if len(lines) > 3: print("      -> ... (ve diğerleri)")
            else:
                print(f"   🔎 [SİSTEM - BULUNAN ENTEGRASYON]: (Veri Bulunamadı - Boş Dönüş)")
                
            print(f"🗣️ ASİSTAN: {ai_response}")
            
            # Update history
            history += f"User: {user_text}\nAssistant: {ai_response}\n"
            is_first = False
            
            # Simulate slight delay for readability
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"\n❌ HATA: {e}")
            import traceback
            traceback.print_exc()
            
    print("\n--- 🏁 SİMÜLASYON TAMAMLANDI 🏁 ---")

if __name__ == "__main__":
    asyncio.run(run_simulation())
