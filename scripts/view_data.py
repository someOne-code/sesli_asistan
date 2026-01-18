import sys
import os
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def view_data():
    db_path = "hedef.db"
    if not os.path.exists(db_path):
        print(f"❌ Error: '{db_path}' not found.")
        return

    engine = create_engine(f"sqlite:///{db_path}")
    connection = engine.connect()

    while True:
        print("\n" + "="*50)
        print("🕵️  DATABASE INSPECTOR (Truth Verifier)")
        print("="*50)
        print("1. List Top 20 Artists")
        print("2. Search for an Artist (and see their albums)")
        print("3. Search for a Song (Track)")
        print("4. Show Most Expensive Tracks")
        print("5. Custom SQL Query")
        print("0. Exit")
        
        choice = input("\nSelect an option (0-5): ").strip()
        
        if choice == "0":
            break
            
        try:
            if choice == "1":
                print("\n--- TOP 20 ARTISTS ---")
                result = connection.execute(text("SELECT ArtistId, Name FROM Artist LIMIT 20")).fetchall()
                for row in result:
                    print(f"[{row.ArtistId}] {row.Name}")
                    
            elif choice == "2":
                name = input("Enter artist name (e.g. Metallica): ")
                print(f"\n--- ALBUMS BY '{name}' ---")
                # Find artist IDs first
                artists = connection.execute(text(f"SELECT ArtistId, Name FROM Artist WHERE Name LIKE '%{name}%'")).fetchall()
                
                if not artists:
                    print("No artist found.")
                else:
                    for art in artists:
                        print(f"\nArtist: {art.Name}")
                        albums = connection.execute(text(f"SELECT Title FROM Album WHERE ArtistId = {art.ArtistId}")).fetchall()
                        if albums:
                            for alb in albums:
                                print(f"  - 💿 {alb.Title}")
                        else:
                            print("  (No albums found)")

            elif choice == "3":
                term = input("Enter song name (e.g. One): ")
                print(f"\n--- TRACKS MATCHING '{term}' ---")
                tracks = connection.execute(text(f"SELECT Name, Composer, UnitPrice FROM Track WHERE Name LIKE '%{term}%' LIMIT 20")).fetchall()
                for t in tracks:
                    print(f"🎵 {t.Name} | Composer: {t.Composer} | Price: {t.UnitPrice}")

            elif choice == "4":
                print("\n--- MOST EXPENSIVE TRACKS ---")
                tracks = connection.execute(text("SELECT Name, UnitPrice FROM Track ORDER BY UnitPrice DESC, Name ASC LIMIT 10")).fetchall()
                for t in tracks:
                    print(f"💰 {t.UnitPrice} - {t.Name}")

            elif choice == "5":
                query = input("Enter SQL: ")
                result = connection.execute(text(query)).fetchall()
                print("\n--- RESULT ---")
                for row in result:
                    print(row)
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")

    connection.close()
    print("Bye!")

if __name__ == "__main__":
    view_data()
