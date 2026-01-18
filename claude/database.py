from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, List, Dict
import json
from config import settings, logger

Base = declarative_base()


class CallLog(Base):
    """Call logs table for analytics and tracking"""
    __tablename__ = 'call_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    customer_text = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)
    intent = Column(String(50), nullable=True)


class DatabaseManager:
    """Manages all database operations"""
    
    def __init__(self, db_url: Optional[str] = None):
        # Use provided URL or build from settings
        if db_url:
            if "://" not in db_url:
                self.db_url = f"sqlite:///{db_url}"
            else:
                self.db_url = db_url
        else:
            if settings.DB_URL:
                self.db_url = settings.DB_URL
            else:
                self.db_url = f"sqlite:///{settings.DB_NAME}"
        
        # Create engine with appropriate settings
        connect_args = {"check_same_thread": False} if "sqlite" in self.db_url else {}
        self.engine = create_engine(self.db_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Ensure CallLog table exists
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables initialized")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
    
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()
    
    def get_schema_info(self) -> str:
        """
        Retrieves complete schema information including:
        - Tables and columns with types
        - Primary keys
        - Foreign key relationships
        """
        try:
            inspector = inspect(self.engine)
            schema_str = "DATABASE SCHEMA:\n\n"
            
            for table_name in inspector.get_table_names():
                # Skip internal/log tables
                if table_name in ['call_logs', 'sqlite_sequence']:
                    continue
                
                schema_str += f"Table: {table_name}\n"
                
                # Get Columns
                columns = inspector.get_columns(table_name)
                col_strs = []
                for col in columns:
                    col_str = f"  - {col['name']} ({col['type']})"
                    if col.get('primary_key'):
                        col_str += " [PRIMARY KEY]"
                    if not col.get('nullable', True):
                        col_str += " [NOT NULL]"
                    col_strs.append(col_str)
                
                schema_str += "\n".join(col_strs) + "\n"
                
                # Get Foreign Keys
                fks = inspector.get_foreign_keys(table_name)
                if fks:
                    schema_str += "  Relationships:\n"
                    for fk in fks:
                        constrained = ", ".join(fk['constrained_columns'])
                        referred = ", ".join(fk['referred_columns'])
                        referred_table = fk['referred_table']
                        schema_str += f"    - {constrained} → {referred_table}.{referred}\n"
                
                schema_str += "\n"
            
            return schema_str
        except Exception as e:
            logger.error(f"❌ Error getting schema info: {e}")
            return ""
    
    def get_sample_data(self) -> str:
        """Retrieves sample data from all tables for identity generation"""
        try:
            inspector = inspect(self.engine)
            sample_data = "SAMPLE DATA:\n\n"
            
            with self.engine.connect() as conn:
                for table_name in inspector.get_table_names():
                    # Skip internal tables
                    if table_name in ['call_logs', 'sqlite_sequence']:
                        continue
                    
                    try:
                        result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 3"))
                        rows = result.fetchall()
                        if rows:
                            sample_data += f"Table: {table_name}\n"
                            for row in rows:
                                sample_data += f"  {dict(zip(result.keys(), row))}\n"
                            sample_data += "\n"
                    except Exception as e:
                        logger.warning(f"⚠️ Could not get sample data from {table_name}: {e}")
                        continue
            
            return sample_data
        except Exception as e:
            logger.error(f"❌ Error getting sample data: {e}")
            return ""
    
    def run_sql_query(self, sql_query: str) -> str:
        """
        Executes SQL query safely and returns formatted results.
        
        Returns:
            - Formatted results as string
            - Error codes: ÜRÜN_KATEGORISI_YOK, SONUC_YOK, SQL_HATASI, GUVENLIK_UYARISI
        """
        # Handle special markers
        if "SELECT 'YOK'" in sql_query:
            return "ÜRÜN_KATEGORISI_YOK"
        
        try:
            # Security check - prevent destructive operations
            forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
            query_upper = sql_query.upper()
            
            for keyword in forbidden:
                if keyword in query_upper:
                    logger.warning(f"⚠️ Blocked unsafe query containing '{keyword}': {sql_query[:100]}")
                    return "GUVENLIK_UYARISI"
            
            # Execute query
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                
                if not rows:
                    logger.info("ℹ️ Query returned no results")
                    return "SONUC_YOK"
                
                # Convert to list of dicts for better formatting
                columns = result.keys()
                formatted_results = []
                
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Convert datetime to string for JSON serialization
                        if isinstance(value, datetime):
                            value = value.isoformat()
                        row_dict[col] = value
                    formatted_results.append(row_dict)
                
                logger.info(f"✅ Query returned {len(formatted_results)} rows")
                return json.dumps(formatted_results, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"❌ SQL Execution Error: {e}")
            logger.error(f"Query was: {sql_query}")
            return f"SQL_HATASI: {str(e)}"
    
    def log_call(
        self, 
        customer_text: str, 
        ai_response: str, 
        sentiment: str, 
        summary: Optional[str] = None,
        session_id: Optional[str] = None,
        intent: Optional[str] = None
    ) -> None:
        """Log a call interaction to the database"""
        session = self.get_session()
        try:
            log_entry = CallLog(
                customer_text=customer_text,
                ai_response=ai_response,
                sentiment=sentiment,
                summary=summary,
                session_id=session_id,
                intent=intent
            )
            session.add(log_entry)
            session.commit()
            logger.info(f"📝 Call logged: session={session_id}, intent={intent}")
        except Exception as e:
            logger.error(f"❌ Failed to log call: {e}")
            session.rollback()
        finally:
            session.close()
    
    def get_call_logs(self, limit: int = 100, session_id: Optional[str] = None) -> List[Dict]:
        """Retrieve call logs from database"""
        session = self.get_session()
        try:
            query = session.query(CallLog).order_by(CallLog.timestamp.desc())
            
            if session_id:
                query = query.filter(CallLog.session_id == session_id)
            
            logs = query.limit(limit).all()
            
            results = []
            for log in logs:
                results.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'customer_text': log.customer_text,
                    'ai_response': log.ai_response,
                    'sentiment': log.sentiment,
                    'summary': log.summary,
                    'session_id': log.session_id,
                    'intent': log.intent
                })
            
            return results
        except Exception as e:
            logger.error(f"❌ Failed to retrieve call logs: {e}")
            return []
        finally:
            session.close()
    
    def get_statistics(self) -> Dict:
        """Get usage statistics"""
        session = self.get_session()
        try:
            total_calls = session.query(CallLog).count()
            
            # Sentiment breakdown
            sentiments = session.query(
                CallLog.sentiment,
                text('COUNT(*) as count')
            ).group_by(CallLog.sentiment).all()
            
            # Intent breakdown
            intents = session.query(
                CallLog.intent,
                text('COUNT(*) as count')
            ).group_by(CallLog.intent).all()
            
            return {
                'total_calls': total_calls,
                'sentiments': {s[0]: s[1] for s in sentiments if s[0]},
                'intents': {i[0]: i[1] for i in intents if i[0]}
            }
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False