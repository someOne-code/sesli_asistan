"""
Generic Query Executor - Safe and Flexible
Allows dynamic queries while maintaining security through whitelisting.
"""
from sqlalchemy import text
from typing import Dict, List, Any, Optional
import re

class SafeQueryExecutor:
    """
    Executes dynamic queries with strict security controls.
    Only SELECT operations on whitelisted tables allowed.
    """
    
    # Forbidden tables (sensitive data)
    FORBIDDEN_TABLES = {"CallLog", "Employee", "Customer", "Invoice", "InvoiceLine"} 
    
    # Only read operations allowed
    ALLOWED_OPERATIONS = ["SELECT"]
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.allowed_tables = set()
        self._discover_tables()

    def _discover_tables(self):
        """Dynamically discover tables from the database engine."""
        from sqlalchemy import inspect
        try:
            # Create a temporary session to get the engine
            session = self.session_factory()
            engine = session.get_bind()
            inspector = inspect(engine)
            
            all_tables = inspector.get_table_names()
            
            # Filter tables
            for table in all_tables:
                # Case-insensitive check against forbidden tables
                if not any(f.lower() == table.lower() for f in self.FORBIDDEN_TABLES):
                    self.allowed_tables.add(table)
            
            print(f"[SafeQueryExecutor] Allowed Tables Discovered: {self.allowed_tables}")
            session.close()
        except Exception as e:
            print(f"[SafeQueryExecutor] Discovery Error: {e}")
            # Fallback to critical music tables if discovery fails
            self.allowed_tables = {"Track", "Album", "Artist", "Genre"}
    
    def execute_generic_query(self, query_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query from structured specification.
        
        Args:
            query_spec: {
                "table": "Track",
                "columns": ["Name", "Artist"],  # optional, default: all
                "filters": [{"column": "GenreId", "operator": "=", "value": 1}],
                "order_by": "Name",
                "limit": 10
            }
        
        Returns:
            List of dicts with results
        """
        table = query_spec.get("table")
        
        # SECURITY: Validate table whitelist
        if not self._is_table_allowed(table):
            raise ValueError(f"Table '{table}' not in whitelist")
        
        # Build safe SQL
        sql = self._build_safe_sql(query_spec)
        
        if "params" not in query_spec:
             params = {}
             if "filters" in query_spec:
                 for f in query_spec["filters"]:
                     col = f["column"]
                     val = f.get("value")
                     params[col] = val
        else:
             params = query_spec["params"]

        # Execute with session
        with self.session_factory() as session:
            result = session.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
    
    def _is_table_allowed(self, table: str) -> bool:
        """Check if table is in dynamically discovered whitelist."""
        return table in self.allowed_tables
    
    def _build_safe_sql(self, spec: Dict) -> str:
        """
        Build SQL from spec with parameterized queries.
        Always uses placeholders to prevent SQL injection.
        """
        table = spec["table"]
        columns = spec.get("columns", ["*"])
        
        # SELECT clause
        cols_str = ", ".join(columns) if columns != ["*"] else "*"
        sql = f"SELECT {cols_str} FROM {table}"
        
        # WHERE clause (parameterized)
        filters = spec.get("filters", [])
        if filters:
            conditions = []
            for f in filters:
                col = f["column"]
                op = f.get("operator", "=")
                
                # Special operator: IN_ARTIST - converts artist name to ArtistId via subquery
                if op == "IN_ARTIST":
                    artist_name = f.get("value", "")
                    conditions.append(f"{col} IN (SELECT ArtistId FROM Artist WHERE Name LIKE :artist_name)")
                    # Add to params manually
                    if "params" not in spec:
                        spec["params"] = {}
                    spec["params"]["artist_name"] = f"%{artist_name}%"
                    continue
                
                # Validate operator
                if op not in ["=", "!=", ">", "<", ">=", "<=", "LIKE"]:
                    raise ValueError(f"Invalid operator: {op}")
                conditions.append(f"{col} {op} :{col}")
            sql += " WHERE " + " AND ".join(conditions)
        
        # ORDER BY
        if "order_by" in spec:
            sql += f" ORDER BY {spec['order_by']}"
        
        # LIMIT
        # Force a hard limit for PHONE assistant to prevent long lists
        requested_limit = int(spec.get("limit", 3))
        safe_limit = min(requested_limit, 3)  # Max 3 rows for phone assistant
        sql += f" LIMIT {safe_limit}"
        
        return sql
    
    def validate_llm_generated_spec(self, spec: Dict) -> bool:
        """
        Additional validation for LLM-generated specs.
        Returns True if safe, raises exception if dangerous.
        """
        # Check for SQL keywords that shouldn't be in column names
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        
        for key, value in spec.items():
            if isinstance(value, str):
                for keyword in dangerous_keywords:
                    if keyword.lower() in value.lower():
                        raise ValueError(f"Dangerous keyword detected: {keyword}")
        
        return True


class HybridRepository:
    """
    Combines manual functions (critical logic) with generic executor (flexibility).
    """
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.generic_executor = SafeQueryExecutor(session_factory)
    
    # ========== CRITICAL BUSINESS LOGIC (Manual Functions) ==========
    
    def get_best_selling_genre(self) -> Dict[str, Any]:
        """Best-selling genre - requires complex JOIN logic."""
        with self.session_factory() as session:
            query = text("""
                SELECT g.Name as genre, SUM(il.Quantity) as total_sales
                FROM Genre g
                JOIN Track t ON g.GenreId = t.GenreId
                JOIN InvoiceLine il ON t.TrackId = il.TrackId
                GROUP BY g.Name
                ORDER BY total_sales DESC
                LIMIT 1
            """)
            result = session.execute(query).fetchone()
            return {"genre": result[0], "sales": result[1]} if result else None
    
    # ========== GENERIC QUERIES (Flexible Executor) ==========
    
    def execute_flexible_query(self, llm_query_spec: Dict) -> List[Dict]:
        """
        Execute LLM-generated query with validation.
        
        Example LLM output:
        {
            "table": "Track",
            "filters": [{"column": "GenreId", "operator": "=", "value": 1}],
            "limit": 5
        }
        """
        # Validate
        self.generic_executor.validate_llm_generated_spec(llm_query_spec)
        
        # Execute
        return self.generic_executor.execute_generic_query(llm_query_spec)
