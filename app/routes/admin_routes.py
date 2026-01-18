# API routes for Admin Dashboard
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Global reference - will be set by main.py
db_repo = None

def set_db_repo(repo):
    global db_repo
    db_repo = repo

@router.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get paginated call logs."""
    if db_repo is None:
        return {"error": "Database not initialized"}
    
    logs = db_repo.get_logs(limit=limit, offset=offset)
    return {"logs": logs, "limit": limit, "offset": offset}

@router.get("/stats")
async def get_stats():
    """Get dashboard statistics."""
    if db_repo is None:
        return {"error": "Database not initialized"}
    
    stats = db_repo.get_dashboard_stats()
    return stats

@router.get("/analytics")
async def get_analytics():
    """Get full analytics data for dashboard charts."""
    if db_repo is None:
        return {"error": "Database not initialized"}
    
    # Aggregate all analytics data
    stats = db_repo.get_advanced_stats()
    call_volume = db_repo.get_call_volume_by_day(days=7)
    intent_distribution = db_repo.get_intent_distribution()
    top_searched_terms = db_repo.get_top_searched_terms(limit=10)
    
    return {
        "stats": stats,
        "call_volume": call_volume,
        "intent_distribution": intent_distribution,
        "top_searched_terms": top_searched_terms
    }
