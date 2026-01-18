"""
Safe Service Layer - Chinook Database için optimize edilmiş
AI has zero knowledge of sensitive data tables.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy import text
from datetime import datetime
from config import logger, LogEmoji
from database import DatabaseManager


class SafeService:
    """
    Service layer that provides controlled access to public music data only.
    Handles all database operations with parameterized queries.
    AI cannot generate SQL - only requests pre-defined actions.
    """
    
    # Define public schema that AI can "see" - GERÇEK CHINOOK ŞEMASI
    PUBLIC_SCHEMA = """
DATABASE SCHEMA (Music Catalog Only):

Table: Album
  - AlbumId (INTEGER) [PRIMARY KEY]
  - Title (NVARCHAR(160))
  - ArtistId (INTEGER) → Artist.ArtistId

Table: Artist
  - ArtistId (INTEGER) [PRIMARY KEY]
  - Name (NVARCHAR(120))

Table: Track
  - TrackId (INTEGER) [PRIMARY KEY]
  - Name (NVARCHAR(200))
  - AlbumId (INTEGER) → Album.AlbumId
  - MediaTypeId (INTEGER) → MediaType.MediaTypeId
  - GenreId (INTEGER) → Genre.GenreId
  - Composer (NVARCHAR(220))
  - Milliseconds (INTEGER)
  - Bytes (INTEGER)
  - UnitPrice (NUMERIC(10,2))

Table: Genre
  - GenreId (INTEGER) [PRIMARY KEY]
  - Name (NVARCHAR(120))

Table: MediaType
  - MediaTypeId (INTEGER) [PRIMARY KEY]
  - Name (NVARCHAR(120))

Table: Playlist
  - PlaylistId (INTEGER) [PRIMARY KEY]
  - Name (NVARCHAR(120))

Table: PlaylistTrack
  - PlaylistId (INTEGER, PRIMARY KEY) → Playlist.PlaylistId
  - TrackId (INTEGER, PRIMARY KEY) → Track.TrackId

SCOPE: You can only access music catalog information (albums, artists, tracks, genres, playlists).
FORBIDDEN: You do NOT have access to Customer, Employee, Invoice, InvoiceLine, or call_logs tables.
"""
    
    # Define allowed actions (whitelist approach)
    ALLOWED_ACTIONS = {
        'SEARCH_TRACKS',
        'SEARCH_ALBUMS',
        'SEARCH_ARTISTS',
        'GET_ALBUM_DETAILS',
        'GET_ARTIST_ALBUMS',
        'GET_TRACKS_BY_GENRE',
        'GET_TRACKS_BY_ALBUM',
        'GET_PLAYLIST_DETAILS',
        'GET_PLAYLIST_TRACKS',
        'GET_CHEAPEST_TRACKS',
        'GET_MOST_EXPENSIVE_TRACKS',
        'LIST_GENRES',
        'LIST_MEDIA_TYPES',
        'GET_TRACK_DETAILS',
        'GET_ARTIST_DETAILS'
    }
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.engine = db_manager.engine
        logger.info(f"{LogEmoji.CHECK} SafeService initialized with Chinook database schema")
    
    def get_public_schema(self) -> str:
        """Returns only the public schema that AI can see"""
        return self.PUBLIC_SCHEMA
    
    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a pre-defined action with parameters.
        This is the ONLY way AI can access data.
        
        Args:
            action: Action name from ALLOWED_ACTIONS
            params: Parameters for the action
            
        Returns:
            Dict with status and data/error
        """
        # Validate action
        if action not in self.ALLOWED_ACTIONS:
            logger.warning(f"{LogEmoji.WARNING} Unauthorized action attempted: {action}")
            return {
                'status': 'error',
                'error': 'UNAUTHORIZED_ACTION',
                'message': 'This action is not allowed.'
            }
        
        # Route to appropriate method
        try:
            method_name = action.lower()
            method = getattr(self, method_name, None)
            
            if method is None:
                return {
                    'status': 'error',
                    'error': 'NOT_IMPLEMENTED',
                    'message': f'Action {action} is not implemented yet.'
                }
            
            result = method(**params)
            logger.info(f"{LogEmoji.CHECK} Action {action} executed successfully")
            
            return {
                'status': 'success',
                'action': action,
                'data': result
            }
            
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Error executing action {action}: {e}")
            return {
                'status': 'error',
                'error': 'EXECUTION_FAILED',
                'message': str(e)
            }
    
    # ==================== MUSIC CATALOG METHODS - CHINOOK OPTIMIZED ====================
    
    def search_tracks(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Search tracks by name or composer"""
        query = text("""
            SELECT 
                t.TrackId,
                t.Name AS TrackName,
                t.Composer,
                t.UnitPrice,
                t.Milliseconds,
                a.Title AS AlbumTitle,
                ar.Name AS ArtistName,
                g.Name AS GenreName,
                m.Name AS MediaType
            FROM Track t
            LEFT JOIN Album a ON t.AlbumId = a.AlbumId
            LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
            LEFT JOIN Genre g ON t.GenreId = g.GenreId
            LEFT JOIN MediaType m ON t.MediaTypeId = m.MediaTypeId
            WHERE t.Name LIKE :keyword OR t.Composer LIKE :keyword
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'keyword': f'%{keyword}%',
                'limit': limit
            })
            return [dict(row._mapping) for row in result]
    
    def search_albums(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Search albums by title"""
        query = text("""
            SELECT 
                a.AlbumId,
                a.Title AS AlbumTitle,
                ar.Name AS ArtistName,
                ar.ArtistId
            FROM Album a
            LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
            WHERE a.Title LIKE :keyword
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'keyword': f'%{keyword}%',
                'limit': limit
            })
            return [dict(row._mapping) for row in result]
    
    def search_artists(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Search artists by name"""
        query = text("""
            SELECT 
                ArtistId,
                Name AS ArtistName
            FROM Artist
            WHERE Name LIKE :keyword
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'keyword': f'%{keyword}%',
                'limit': limit
            })
            return [dict(row._mapping) for row in result]
    
    def get_album_details(self, album_id: int) -> Dict:
        """Get detailed information about an album"""
        query = text("""
            SELECT 
                a.AlbumId,
                a.Title AS AlbumTitle,
                ar.Name AS ArtistName,
                ar.ArtistId,
                COUNT(t.TrackId) AS TrackCount,
                SUM(t.Milliseconds) AS TotalDuration,
                AVG(t.UnitPrice) AS AvgPrice,
                MIN(t.UnitPrice) AS MinPrice,
                MAX(t.UnitPrice) AS MaxPrice
            FROM Album a
            LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
            LEFT JOIN Track t ON a.AlbumId = t.AlbumId
            WHERE a.AlbumId = :album_id
            GROUP BY a.AlbumId, a.Title, ar.Name, ar.ArtistId
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'album_id': album_id})
            row = result.fetchone()
            return dict(row._mapping) if row else {}
    
    def get_artist_albums(self, artist_name: str, limit: int = 10) -> List[Dict]:
        """Get all albums by an artist"""
        query = text("""
            SELECT 
                a.AlbumId,
                a.Title AS AlbumTitle,
                ar.Name AS ArtistName,
                ar.ArtistId,
                COUNT(t.TrackId) AS TrackCount
            FROM Album a
            JOIN Artist ar ON a.ArtistId = ar.ArtistId
            LEFT JOIN Track t ON a.AlbumId = t.AlbumId
            WHERE ar.Name LIKE :artist_name
            GROUP BY a.AlbumId, a.Title, ar.Name, ar.ArtistId
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'artist_name': f'%{artist_name}%',
                'limit': limit
            })
            return [dict(row._mapping) for row in result]
    
    def get_artist_details(self, artist_name: str) -> Dict:
        """Get artist details with statistics"""
        query = text("""
            SELECT 
                ar.ArtistId,
                ar.Name AS ArtistName,
                COUNT(DISTINCT a.AlbumId) AS AlbumCount,
                COUNT(DISTINCT t.TrackId) AS TrackCount
            FROM Artist ar
            LEFT JOIN Album a ON ar.ArtistId = a.ArtistId
            LEFT JOIN Track t ON a.AlbumId = t.AlbumId
            WHERE ar.Name LIKE :artist_name
            GROUP BY ar.ArtistId, ar.Name
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'artist_name': f'%{artist_name}%'})
            row = result.fetchone()
            return dict(row._mapping) if row else {}
    
    def get_tracks_by_genre(self, genre_name: str, limit: int = 5) -> List[Dict]:
        """Get tracks filtered by genre"""
        query = text("""
            SELECT 
                t.TrackId,
                t.Name AS TrackName,
                t.UnitPrice,
                t.Milliseconds,
                a.Title AS AlbumTitle,
                ar.Name AS ArtistName,
                g.Name AS GenreName
            FROM Track t
            LEFT JOIN Album a ON t.AlbumId = a.AlbumId
            LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
            LEFT JOIN Genre g ON t.GenreId = g.GenreId
            WHERE g.Name LIKE :genre_name
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'genre_name': f'%{genre_name}%',
                'limit': limit
            })
            return [dict(row._mapping) for row in result]
    
    def get_tracks_by_album(self, album_id: int) -> List[Dict]:
        """Get all tracks in an album"""
        query = text("""
            SELECT 
                t.TrackId,
                t.Name AS TrackName,
                t.Composer,
                t.Milliseconds,
                t.Bytes,
                t.UnitPrice,
                g.Name AS GenreName,
                m.Name AS MediaType
            FROM Track t
            LEFT JOIN Genre g ON t.GenreId = g.GenreId
            LEFT JOIN MediaType m ON t.MediaTypeId = m.MediaTypeId
            WHERE t.AlbumId = :album_id
            ORDER BY t.TrackId
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'album_id': album_id})
            return [dict(row._mapping) for row in result]
    
    def get_playlist_details(self, playlist_name: str) -> Dict:
        """Get playlist information"""
        query = text("""
            SELECT 
                p.PlaylistId,
                p.Name AS PlaylistName,
                COUNT(pt.TrackId) AS TrackCount
            FROM Playlist p
            LEFT JOIN PlaylistTrack pt ON p.PlaylistId = pt.PlaylistId
            WHERE p.Name LIKE :playlist_name
            GROUP BY p.PlaylistId, p.Name
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'playlist_name': f'%{playlist_name}%'})
            row = result.fetchone()
            return dict(row._mapping) if row else {}
    
    def get_playlist_tracks(self, playlist_id: int, limit: int = 20) -> List[Dict]:
        """Get tracks in a playlist"""
        query = text("""
            SELECT 
                t.TrackId,
                t.Name AS TrackName,
                t.UnitPrice,
                t.Milliseconds,
                a.Title AS AlbumTitle,
                ar.Name AS ArtistName,
                g.Name AS GenreName
            FROM PlaylistTrack pt
            JOIN Track t ON pt.TrackId = t.TrackId
            LEFT JOIN Album a ON t.AlbumId = a.AlbumId
            LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
            LEFT JOIN Genre g ON t.GenreId = g.GenreId
            WHERE pt.PlaylistId = :playlist_id
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                'playlist_id': playlist_id,
                'limit': limit
            })
            return [dict(row._mapping) for row in result]
    
    def get_cheapest_tracks(self, limit: int = 5, genre: Optional[str] = None) -> List[Dict]:
        """Get cheapest tracks, optionally filtered by genre"""
        if genre:
            query = text("""
                SELECT 
                    t.TrackId,
                    t.Name AS TrackName,
                    t.UnitPrice,
                    t.Milliseconds,
                    a.Title AS AlbumTitle,
                    ar.Name AS ArtistName,
                    g.Name AS GenreName
                FROM Track t
                LEFT JOIN Album a ON t.AlbumId = a.AlbumId
                LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
                LEFT JOIN Genre g ON t.GenreId = g.GenreId
                WHERE g.Name LIKE :genre
                ORDER BY t.UnitPrice ASC
                LIMIT :limit
            """)
            params = {'genre': f'%{genre}%', 'limit': limit}
        else:
            query = text("""
                SELECT 
                    t.TrackId,
                    t.Name AS TrackName,
                    t.UnitPrice,
                    t.Milliseconds,
                    a.Title AS AlbumTitle,
                    ar.Name AS ArtistName,
                    g.Name AS GenreName
                FROM Track t
                LEFT JOIN Album a ON t.AlbumId = a.AlbumId
                LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
                LEFT JOIN Genre g ON t.GenreId = g.GenreId
                ORDER BY t.UnitPrice ASC
                LIMIT :limit
            """)
            params = {'limit': limit}
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            return [dict(row._mapping) for row in result]
    
    def get_most_expensive_tracks(self, limit: int = 5, genre: Optional[str] = None) -> List[Dict]:
        """Get most expensive tracks, optionally filtered by genre"""
        if genre:
            query = text("""
                SELECT 
                    t.TrackId,
                    t.Name AS TrackName,
                    t.UnitPrice,
                    t.Milliseconds,
                    a.Title AS AlbumTitle,
                    ar.Name AS ArtistName,
                    g.Name AS GenreName
                FROM Track t
                LEFT JOIN Album a ON t.AlbumId = a.AlbumId
                LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
                LEFT JOIN Genre g ON t.GenreId = g.GenreId
                WHERE g.Name LIKE :genre
                ORDER BY t.UnitPrice DESC
                LIMIT :limit
            """)
            params = {'genre': f'%{genre}%', 'limit': limit}
        else:
            query = text("""
                SELECT 
                    t.TrackId,
                    t.Name AS TrackName,
                    t.UnitPrice,
                    t.Milliseconds,
                    a.Title AS AlbumTitle,
                    ar.Name AS ArtistName,
                    g.Name AS GenreName
                FROM Track t
                LEFT JOIN Album a ON t.AlbumId = a.AlbumId
                LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
                LEFT JOIN Genre g ON t.GenreId = g.GenreId
                ORDER BY t.UnitPrice DESC
                LIMIT :limit
            """)
            params = {'limit': limit}
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            return [dict(row._mapping) for row in result]
    
    def list_genres(self) -> List[Dict]:
        """List all available genres"""
        query = text("""
            SELECT 
                g.GenreId,
                g.Name AS GenreName,
                COUNT(t.TrackId) AS TrackCount
            FROM Genre g
            LEFT JOIN Track t ON g.GenreId = t.GenreId
            GROUP BY g.GenreId, g.Name
            ORDER BY g.Name
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [dict(row._mapping) for row in result]
    
    def list_media_types(self) -> List[Dict]:
        """List all available media types"""
        query = text("""
            SELECT 
                m.MediaTypeId,
                m.Name AS MediaTypeName,
                COUNT(t.TrackId) AS TrackCount
            FROM MediaType m
            LEFT JOIN Track t ON m.MediaTypeId = t.MediaTypeId
            GROUP BY m.MediaTypeId, m.Name
            ORDER BY m.Name
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return [dict(row._mapping) for row in result]
    
    def get_track_details(self, track_id: int) -> Dict:
        """Get detailed information about a specific track"""
        query = text("""
            SELECT 
                t.TrackId,
                t.Name AS TrackName,
                t.Composer,
                t.Milliseconds,
                t.Bytes,
                t.UnitPrice,
                a.Title AS AlbumTitle,
                a.AlbumId,
                ar.Name AS ArtistName,
                ar.ArtistId,
                g.Name AS GenreName,
                g.GenreId,
                m.Name AS MediaType,
                m.MediaTypeId
            FROM Track t
            LEFT JOIN Album a ON t.AlbumId = a.AlbumId
            LEFT JOIN Artist ar ON a.ArtistId = ar.ArtistId
            LEFT JOIN Genre g ON t.GenreId = g.GenreId
            LEFT JOIN MediaType m ON t.MediaTypeId = m.MediaTypeId
            WHERE t.TrackId = :track_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {'track_id': track_id})
            row = result.fetchone()
            return dict(row._mapping) if row else {}
    
    # ==================== INTERNAL ONLY - NOT EXPOSED TO AI ====================
    
    def _log_interaction_to_db(
        self,
        customer_text: str,
        ai_response: str,
        sentiment: str,
        summary: Optional[str] = None,
        session_id: Optional[str] = None,
        intent: Optional[str] = None
    ) -> None:
        """
        INTERNAL METHOD - Log interaction to call_logs table.
        AI has NO KNOWLEDGE of this method.
        Called automatically by the system, never by AI.
        """
        try:
            self.db.log_call(
                customer_text=customer_text,
                ai_response=ai_response,
                sentiment=sentiment,
                summary=summary,
                session_id=session_id,
                intent=intent
            )
        except Exception as e:
            logger.error(f"{LogEmoji.ERROR} Internal logging failed: {e}")