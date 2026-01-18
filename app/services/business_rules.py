"""
Business Logic Layer.
Contains pure business rules, validation, and domain logic.
Decoupled from Infrastructure (DB/AI) and Framework (FastAPI).
"""
from typing import Dict, Any, List, Optional
from app.core.interfaces import IDatabaseRepository

class MusicCatalogBusiness:
    """
    Business rules for Music Catalog operations.
    Enforces validation, defaults, and business policies.
    """
    def __init__(self, db_repo: IDatabaseRepository):
        self.db = db_repo

    def search_tracks(self, keyword: str) -> Dict[str, Any]:
        """
        Search tracks with business validation.
        Rule: Keyword must be at least 2 characters.
        """
        if not keyword or len(keyword.strip()) < 2:
            return {
                "status": "error",
                "message": "Arama terimi en az 2 karakter olmalıdır.",
                "data": []
            }
            
        results = self.db.search_tracks(keyword)
        
        return {
            "status": "success",
            "message": f"{len(results)} parça bulundu.",
            "data": results
        }

    def get_tracks_by_genre(self, genre_name: str) -> Dict[str, Any]:
        """
        Get genre tracks validation.
        Rule: Genre name required.
        """
        if not genre_name:
            return {
                "status": "error",
                "message": "Müzik türü belirtilmelidir.",
                "data": []
            }
            
        results = self.db.get_tracks_by_genre(genre_name)
        return {
            "status": "success", 
            "data": results
        }

    def get_album_details(self, album_name: str) -> Dict[str, Any]:
        if not album_name:
            return {"status": "error", "message": "Albüm adı gerekli."}
            
        result = self.db.get_album_details(album_name)
        if not result:
            return {"status": "error", "message": "Albüm bulunamadı."}
            
        return {"status": "success", "data": result}
        
    def get_budget_friendly_tracks(self, max_price: float = 1.0) -> Dict[str, Any]:
        """
        Example rule: Max price cap check
        """
        if max_price > 100:
             return {"status": "error", "message": "Maximum fiyat limiti aşıldı."}
             
        # Currently repo has get_cheapest, we might map to that or use flexible query
        # For now, mapping to get_cheapest as a proxy for logic demo
        results = self.db.get_cheapest_products()
        return {"status": "success", "data": results}
