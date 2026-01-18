from sqlalchemy import create_engine, text

db_path = "hedef.db"

if not os.path.exists(db_path):
    print(f"HATA: {db_path} bulunamadı!")
    if os.path.exists("chinook.db"):
        print("Uyarı: hedef.db yok, chinook.db kullanılıyor.")
        db_path = "chinook.db"
    else:
        print("HATA: Ne hedef.db ne de chinook.db bulunamadı. Program sonlandırılıyor.")
        exit() # Or sys.exit() if sys is imported

engine = create_engine(f'sqlite:///{db_path}')

with engine.connect() as conn:
    # Metallica şarkılarını ve türlerini kontrol et
    query = text("""
        SELECT 
            Track.Name as Song,
            Genre.Name as Genre,
            Artist.Name as Artist
        FROM Track
        JOIN Genre ON Track.GenreId = Genre.GenreId
        JOIN Album ON Track.AlbumId = Album.AlbumId
        JOIN Artist ON Album.ArtistId = Artist.ArtistId
        WHERE Artist.Name LIKE '%Metallica%'
        LIMIT 10
    """)
    
    results = conn.execute(query)
    
    print("=== METALLICA ŞARKILARI VE TÜRLERİ ===")
    for row in results:
        print(f"{row.Song} - Tür: {row.Genre} - Sanatçı: {row.Artist}")
