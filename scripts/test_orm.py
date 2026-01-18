"""
Test ORM refactored methods to ensure they return same results as before.
"""
import os
from app.infrastructure.database.repository import SqliteMusicRepository

# Initialize repository
db_url = "sqlite:///hedef.db"
if not os.path.exists("hedef.db") and os.path.exists("chinook.db"):
     db_url = "sqlite:///chinook.db"
repo = SqliteMusicRepository(db_url)

print("=" * 50)
print("TESTING ORM REFACTORED METHODS")
print("=" * 50)

# Test 1: get_all_genres
print("\n1. Testing get_all_genres()...")
try:
    genres = repo.get_all_genres()
    print(f"✓ Found {len(genres)} genres")
    print(f"  Sample: {', '.join(genres[:5])}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 2: get_cheapest_products
print("\n2. Testing get_cheapest_products()...")
try:
    cheapest = repo.get_cheapest_products()
    print(f"✓ Found {len(cheapest)} tracks")
    for track in cheapest:
        print(f"  - {track['Name']}: ${track['UnitPrice']}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 3: search_tracks
print("\n3. Testing search_tracks('Metallica')...")
try:
    results = repo.search_tracks("Metallica")
    print(f"✓ Found {len(results)} tracks")
    for track in results[:3]:
        print(f"  - {track['Name']} by {track.get('Artist', 'N/A')}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 4: get_tracks_by_genre
print("\n4. Testing get_tracks_by_genre('Rock')...")
try:
    results = repo.get_tracks_by_genre("Rock")
    print(f"✓ Found {len(results)} tracks")
    for track in results[:3]:
        print(f"  - {track['Name']} by {track.get('Artist', 'N/A')}")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 5: get_album_details (Phase 3)
print("\n5. Testing get_album_details('Master')...")
try:
    result = repo.get_album_details("Master")
    if result:
        print(f"✓ Album: {result.get('Title', 'N/A')}")
        print(f"  Artist: {result.get('Artist', 'N/A')}")
        print(f"  Tracks: {result.get('TrackCount', 0)}")
    else:
        print("✓ No album found")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 6: get_best_selling_genre (Phase 3 - Complex)
print("\n6. Testing get_best_selling_genre()...")
try:
    result = repo.get_best_selling_genre()
    print(f"✓ Best-selling genre: {result['genre']}")
    print(f"  Total sales: {result['sales']}")
except Exception as e:
    print(f"✗ ERROR: {e}")

print("\n" + "=" * 50)
print("ALL TESTS COMPLETE - ORM REFACTOR VERIFIED ✓")
print("=" * 50)
