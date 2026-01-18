import os
import sys

# Setup environment
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_data():
    print(f"Connecting to DB: {settings.DB_NAME}")
    
    # Create engine
    db_url = settings.DB_NAME
    if not db_url.startswith("sqlite"):
        db_url = f"sqlite:///{db_url}"
        
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        print("\n--- CHECKING CHINOOK DATA (Track/Artist Tables) ---")
        
        # Check for Metallica in Artist table
        query_artist = text("SELECT * FROM Artist WHERE Name LIKE :term")
        artists = conn.execute(query_artist, {"term": "%Metallica%"}).fetchall()
        print(f"Found {len(artists)} Artists matching 'Metallica':")
        for a in artists:
            print(f" - {a}")
            
        if artists:
            artist_id = artists[0][0] # Assuming first col is ID
            # Check tracks for this artist
            # Note: Track -> Album -> Artist
            query_tracks = text("""
                SELECT t.Name, a.Title, g.Name as Genre, t.UnitPrice 
                FROM Track t
                JOIN Album a ON t.AlbumId = a.AlbumId
                JOIN Genre g ON t.GenreId = g.GenreId
                WHERE a.ArtistId = :aid
                LIMIT 5
            """)
            tracks = conn.execute(query_tracks, {"aid": artist_id}).fetchall()
            print(f"\nSample Tracks for ArtistID {artist_id}:")
            for t in tracks:
                print(f" - {t}")
        
        # Check searching by name in Track table directly
        query_track_name = text("SELECT count(*) FROM Track WHERE Name LIKE :term")
        count = conn.execute(query_track_name, {"term": "%Metallica%"}).scalar()
        print(f"\nTracks with 'Metallica' in name: {count}")

        # Check searching by name in Track table with Typo/Suffix (simulating "Metallica albümleri")
        term_fail = "%Metallica albümleri%"
        count_fail = conn.execute(query_track_name, {"term": term_fail}).scalar()
        print(f"Tracks with '{term_fail}' in name: {count_fail}")

if __name__ == "__main__":
    check_data()
