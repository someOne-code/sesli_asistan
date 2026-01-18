import atexit
import logging
from typing import Dict
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Global Caches
_ENGINE_CACHE: Dict[str, Engine] = {}
_SESSION_FACTORY_CACHE: Dict[str, sessionmaker] = {}

# NOTE: Thread Lock intentionally omitted to avoid deadlocks in current environment.
# Restore synchronization if high-concurrency race conditions are observed.

def _ensure_url_format(db_url: str) -> str:
    if "://" not in db_url:
        return f"sqlite:///{db_url}"
    return db_url

def get_engine(db_url: str) -> Engine:
    """
    Get or create a SQLAlchemy Engine (Singleton).
    """
    db_url = _ensure_url_format(db_url)

    if db_url in _ENGINE_CACHE:
        return _ENGINE_CACHE[db_url]
    
    # Slow path (no lock)
    if db_url not in _ENGINE_CACHE:
        logger.debug(f"Creating engine for {db_url}")
        
        connect_args = {}
        if "sqlite" in db_url:
            connect_args = {"check_same_thread": False, "timeout": 30}
        
        # Build engine arguments dynamically to avoid invalid parameters for SQLite
        engine_kwargs = {
            "connect_args": connect_args,
            "pool_recycle": 1800,
            "echo": False
        }
        
        if "sqlite" not in db_url:
            engine_kwargs["poolclass"] = QueuePool
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20
            engine_kwargs["pool_timeout"] = 30

        _ENGINE_CACHE[db_url] = create_engine(db_url, **engine_kwargs)
    return _ENGINE_CACHE[db_url]

def get_session_factory(db_url: str) -> sessionmaker:
    db_url = _ensure_url_format(db_url)

    if db_url in _SESSION_FACTORY_CACHE:
        return _SESSION_FACTORY_CACHE[db_url]
    
    if db_url not in _SESSION_FACTORY_CACHE:
        engine = get_engine(db_url)
        _SESSION_FACTORY_CACHE[db_url] = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    return _SESSION_FACTORY_CACHE[db_url]

def dispose_all_engines():
    logger.info("Disposing engines...")
    for db_url, engine in _ENGINE_CACHE.items():
        try:
            engine.dispose()
        except Exception:
            pass
    _ENGINE_CACHE.clear()
    _SESSION_FACTORY_CACHE.clear()

atexit.register(dispose_all_engines)
