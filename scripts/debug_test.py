
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from textwrap import dedent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.models import Base, Genre, Artist, Album, Track, InvoiceLine
from app.infrastructure.database.repository import SqliteMusicRepository

def debug_test():
    try:
        print("Setting up DB...")
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Seed
        rock = Genre(GenreId=1, Name="Rock")
        jazz = Genre(GenreId=2, Name="Jazz")
        session.add(rock)
        session.add(jazz)
        session.commit()
        
        # Repo
        repo = SqliteMusicRepository("sqlite:///:memory:")
        repo.get_session = lambda: session
        repo.engine = engine
        
        # Test get_all_genres
        print("Running get_all_genres...")
        genres = repo.get_all_genres()
        print(f"Result: {genres}")
        
        assert len(genres) == 2
        assert "Rock" in genres
        assert "Jazz" in genres
        assert genres == ["Jazz", "Rock"]
        print("PASS")
        
    except Exception as e:
        print("FAIL")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_test()
