from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from config import settings, logger

Base = declarative_base()

class CallLog(Base):
    __tablename__ = 'call_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    customer_text = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)

class DatabaseManager:
    def __init__(self, db_url: str = None):
        # Use provided URL or build from settings. Default to sqlite if not provided.
        # Ideally, settings.DB_URL should be used, but keeping backward compat with DB_NAME for sqlite
        if db_url:
            if "://" not in db_url:
                self.db_url = f"sqlite:///{db_url}"
            else:
                self.db_url = db_url
        else:
            self.db_url = f"sqlite:///{settings.DB_NAME}"
            
        self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False} if "sqlite" in self.db_url else {})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Ensure CallLog table exists (simple migration)
        # For existing business tables, we assume they exist or are managed elsewhere, 
        # but we need CallLogs for analytics.
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")

    def get_session(self):
        return self.SessionLocal()

    def get_schema_info(self) -> str:
        """
        Retrieves schema information including Foreign Keys.
        Excludes sensitive tables (Customer, Employee, Invoice, etc.) to protect PII.
        """
        inspector = inspect(self.engine)
        schema_str = ""
        
        SENSITIVE_TABLES = ['Customer', 'Employee', 'Invoice', 'InvoiceLine', 'call_logs']

        for table_name in inspector.get_table_names():
            if table_name in SENSITIVE_TABLES:
                continue

            # Get Columns
            columns = inspector.get_columns(table_name)
            col_strs = [f"{col['name']} ({col['type']})" for col in columns]
            
            # Get Foreign Keys
            fks = inspector.get_foreign_keys(table_name)
            fk_strs = []
            for fk in fks:
                # "constrained_columns" -> "referred_table"."referred_columns"
                constrained = ", ".join(fk['constrained_columns'])
                referred = ", ".join(fk['referred_columns'])
                fk_strs.append(f"FOREIGN KEY ({constrained}) REFERENCES {fk['referred_table']}({referred})")
            
            schema_str += f"\nTable: {table_name}\n"
            schema_str += f"  Columns: {', '.join(col_strs)}\n"
            if fk_strs:
                schema_str += f"  Relationships: {'; '.join(fk_strs)}\n"
                
        return schema_str

    def get_sample_data(self) -> str:
        """Retrieves sample data for company identity generation."""
        try:
            inspector = inspect(self.engine)
            ornek_veriler = ""
            SENSITIVE_TABLES = ['Customer', 'Employee', 'Invoice', 'InvoiceLine', 'call_logs']
            
            with self.engine.connect() as conn:
                for table_name in inspector.get_table_names():
                    if table_name in SENSITIVE_TABLES:
                        continue
                    try:
                        result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                        rows = result.fetchall()
                        if rows:
                            ornek_veriler += f"\nTable: {table_name} -> Data: {str(rows)}"
                    except Exception as e:
                        pass
            return ornek_veriler
        except Exception as e:
            logger.error(f"Error getting sample data: {e}")
            return ""

    def log_call(self, customer_text: str, ai_response: str, sentiment: str, summary: str):
        session = self.get_session()
        try:
            log_entry = CallLog(
                customer_text=customer_text,
                ai_response=ai_response,
                sentiment=sentiment,
                summary=summary
            )
            session.add(log_entry)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log call: {e}")
            session.rollback()
        finally:
            session.close()

class SafeService:
    """
    Middle Layer Service for secure data access.
    Isolates the AI from direct database queries.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def search_tracks(self, keyword: str) -> str:
        """Searches tracks by name or composer."""
        query = text("""
            SELECT Track.Name, Album.Title, Artist.Name as Artist, Track.UnitPrice 
            FROM Track 
            JOIN Album ON Track.AlbumId = Album.AlbumId 
            JOIN Artist ON Album.ArtistId = Artist.ArtistId
            WHERE Track.Name LIKE :kw OR Track.Composer LIKE :kw
            LIMIT 5
        """)
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(query, {"kw": f"%{keyword}%"})
                rows = result.fetchall()
                if not rows: return "No tracks found matching that keyword."
                return str(rows)
        except Exception as e:
            logger.error(f"Search tracks error: {e}")
            return "Error searching tracks."

    def get_tracks_by_genre(self, genre_name: str) -> str:
        """Fetches tracks for a specific genre."""
        query = text("""
            SELECT Track.Name, Artist.Name, Track.UnitPrice 
            FROM Track
            JOIN Genre ON Track.GenreId = Genre.GenreId
            JOIN Album ON Track.AlbumId = Album.AlbumId
            JOIN Artist ON Album.ArtistId = Artist.ArtistId
            WHERE Genre.Name LIKE :g
            LIMIT 5
        """)
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(query, {"g": f"%{genre_name}%"})
                rows = result.fetchall()
                if not rows: return f"No tracks found for genre '{genre_name}'."
                return str(rows)
        except Exception as e:
            logger.error(f"Genre search error: {e}")
            return "Error searching genre."

    def get_album_details(self, album_name: str) -> str:
        """Gets details of an album."""
        query = text("""
            SELECT Album.Title, Artist.Name, count(Track.TrackId) as TrackCount
            FROM Album
            JOIN Artist ON Album.ArtistId = Artist.ArtistId
            LEFT JOIN Track ON Album.AlbumId = Track.AlbumId
            WHERE Album.Title LIKE :a
            GROUP BY Album.AlbumId
            LIMIT 1
        """)
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(query, {"a": f"%{album_name}%"})
                row = result.fetchone()
                if not row: return "Album not found."
                return str(row)
        except Exception as e:
            logger.error(f"Album details error: {e}")
            return "Error getting album details."
    
    def get_cheapest_products(self) -> str:
        query = text("SELECT Name, UnitPrice FROM Track ORDER BY UnitPrice ASC LIMIT 3")
        try:
            with self.db.engine.connect() as conn:
                rows = conn.execute(query).fetchall()
                return str(rows)
        except Exception as e: return str(e)

    def get_most_expensive_products(self) -> str:
        query = text("SELECT Name, UnitPrice FROM Track ORDER BY UnitPrice DESC LIMIT 3")
        try:
            with self.db.engine.connect() as conn:
                rows = conn.execute(query).fetchall()
                return str(rows)
        except Exception as e: return str(e)
