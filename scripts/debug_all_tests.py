
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.models import Base, Genre, Artist, Album, Track, InvoiceLine
from app.infrastructure.database.repository import SqliteMusicRepository

def setup_repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Seed
    rock = Genre(GenreId=1, Name="Rock")
    jazz = Genre(GenreId=2, Name="Jazz")
    session.add_all([rock, jazz])
    
    metallica = Artist(ArtistId=1, Name="Metallica")
    miles = Artist(ArtistId=2, Name="Miles Davis")
    session.add_all([metallica, miles])
    
    master = Album(AlbumId=1, Title="Master of Puppets", ArtistId=1)
    blue = Album(AlbumId=2, Title="Kind of Blue", ArtistId=2)
    session.add_all([master, blue])
    
    t1 = Track(TrackId=1, Name="Battery", AlbumId=1, GenreId=1, Composer="Hetfield", UnitPrice=0.99)
    t2 = Track(TrackId=2, Name="So What", AlbumId=1, GenreId=1, Composer="Hetfield", UnitPrice=1.99)
    t3 = Track(TrackId=3, Name="Blue in Green", AlbumId=2, GenreId=2, Composer="Davis", UnitPrice=0.99)
    session.add_all([t1, t2, t3])
    
    inv1 = InvoiceLine(InvoiceLineId=1, InvoiceId=1, TrackId=1, UnitPrice=0.99, Quantity=100)
    inv2 = InvoiceLine(InvoiceLineId=2, InvoiceId=2, TrackId=3, UnitPrice=0.99, Quantity=50)
    session.add_all([inv1, inv2])
    
    session.commit()
    
    repo = SqliteMusicRepository("sqlite:///:memory:")
    repo.get_session = lambda: session
    repo.engine = engine
    return repo

def run_tests():
    repo = setup_repo()
    failures = []
    
    # Test 1
    try:
        print("Test 1: get_all_genres...", end="")
        genres = repo.get_all_genres()
        assert len(genres) == 2
        assert genres == ["Jazz", "Rock"]
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failures.append("test_get_all_genres")

    # Test 2
    try:
        print("Test 2: search_tracks...", end="")
        results = repo.search_tracks("Battery")
        assert len(results) == 1
        assert results[0]['Name'] == "Battery"
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failures.append("test_search_tracks")

    # Test 3
    try:
        print("Test 3: get_tracks_by_genre...", end="")
        results = repo.get_tracks_by_genre("Rock")
        assert len(results) == 2
        results = repo.get_tracks_by_genre("Jazz")
        assert len(results) == 1
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failures.append("test_get_tracks_by_genre")
        
    # Test 4
    try:
        print("Test 4: get_best_selling_genre...", end="")
        result = repo.get_best_selling_genre()
        assert result['genre'] == "Rock"
        assert result['sales'] == 100
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failures.append("test_get_best_selling_genre")

    # Test 5
    try:
        print("Test 5: get_album_details...", end="")
        result = repo.get_album_details("Master")
        assert result['Title'] == "Master of Puppets"
        assert result['TrackCount'] == 2
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failures.append("test_get_album_details")
        
    # Test 6
    try:
        print("Test 6: get_cheapest_products...", end="")
        # Battery (0.99), So What (1.99), Blue in Green (0.99)
        results = repo.get_cheapest_products()
        assert len(results) == 3
        # Should be sorted
        assert results[0]['UnitPrice'] == 0.99
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failures.append("test_get_cheapest_products")

    if failures:
        print(f"\nFAILURES: {failures}")
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
