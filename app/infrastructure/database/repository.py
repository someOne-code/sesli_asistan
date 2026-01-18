from sqlalchemy import create_engine, text, inspect, or_, func
from sqlalchemy.orm import sessionmaker
from app.core.interfaces import IDatabaseRepository
from app.infrastructure.database.models import Base, BusinessOffering, CompanyInfo, CallLog, Tenant
from app.domain.models import Product
from typing import List, Dict, Any, Optional
import re
from app.infrastructure.database.engine_manager import get_session_factory, get_engine

class HedefRepository(IDatabaseRepository):
    """
    Implementation of Universal Retrieval for multitenant SaaS.
    """
    def __init__(self, db_url: str):
        if "://" not in db_url:
            self.db_url = f"sqlite:///{db_url}"
        else:
            self.db_url = db_url
            
        self.session_factory = get_session_factory(self.db_url)
        self.engine = get_engine(self.db_url)
        
        # Auto-Migration for Demo Simplicity (creates new tables)
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            print(f"Schema Init Warning: {e}")

    def get_session(self):
        return self.session_factory()

    def search_products(
        self,
        query: Optional[str],
        limit: int = 10,
        filters: Optional[dict] = None,
        tenant_id: Optional[str] = None
    ) -> List[Product]:
        """
        Search products in BusinessOfferings table.
        Optimized for Tenant Isolation.
        """
        session = self.get_session()
        products = []
        try:
            db_query = session.query(BusinessOffering)
            
            # 1. Tenant Filter (Mandatory for SaaS)
            # 1. Tenant Filter (Mandatory for SaaS)
            if not tenant_id:
                # CRITICAL SECURITY: Never return data without tenant_id
                print("SECURITY WARNING: search_products called without tenant_id. Returning empty.")
                return []
            
            db_query = db_query.filter(BusinessOffering.tenant_id == tenant_id)
            
            # 2. Text Search
            if query:
                # Simple case-insensitive LIKE
                term = f"%{query}%"
                db_query = db_query.filter(or_(
                    BusinessOffering.name.like(term),
                    BusinessOffering.description.like(term),
                    BusinessOffering.category.like(term)
                ))
            
            # 3. Filters
            if filters and filters.get('sort') == 'price_asc':
                db_query = db_query.order_by(BusinessOffering.price.asc())
            elif filters and filters.get('sort') == 'price_desc':
                db_query = db_query.order_by(BusinessOffering.price.desc())
            else:
                db_query = db_query.order_by(BusinessOffering.name.asc())
                
            results = db_query.limit(limit).all()
            
            # --- FALLBACK 2: ADVANCED FUZZY MATCH (Memory Based) ---
            if not results and query:
                # If SQL strategies fail, load names into memory and use difflib
                # This is "Level 3" fuzzy search logic.
                try:
                    import difflib
                    
                    # Fetch only ID and Name to be lightweight
                    all_products_q = session.query(BusinessOffering.id, BusinessOffering.name).filter(BusinessOffering.tenant_id == tenant_id)
                    all_products = all_products_q.all() # List of (id, name)
                    
                    # Create a map and list of names
                    name_map = {p.name: p.id for p in all_products}
                    all_names = list(name_map.keys())
                    
                    # Find closest matches (cutoff=0.6 means 60% similarity)
                    # We check the whole query against product names
                    matches = difflib.get_close_matches(query, all_names, n=limit, cutoff=0.55)
                    
                    if matches:
                        match_ids = [name_map[m] for m in matches]
                        results = session.query(BusinessOffering).filter(BusinessOffering.id.in_(match_ids)).all()
                        
                except Exception as ex:
                    print(f"Fuzzy Logic Error: {ex}")
            # -------------------------------------------------------

            # --- FALLBACK 3: PHONETIC MATCH (Metaphone-lite) ---
            if not results and query:
                try:
                    def _phonetic(text):
                        if not text: return ""
                        # 1. Normalize TR & Case
                        t = text.upper()
                        tr_map = str.maketrans("ÇĞIİÖŞÜ", "CGIIOSU")
                        t = t.translate(tr_map)
                        
                        # 2. Phonetic Replacements (Hybrid TR/EN)
                        t = t.replace("PH", "F").replace("SH", "S").replace("CH", "C")
                        t = t.replace("J", "C").replace("Y", "I").replace("Q", "K").replace("X", "KS")
                        
                        # 3. Remove vowels (except first)
                        if len(t) > 1:
                            first = t[0]
                            rest = t[1:]
                            for v in "AEIOU":
                                rest = rest.replace(v, "")
                            t = first + rest
                            
                        # 4. Dedup (AA -> A)
                        res = []
                        last = None
                        for c in t:
                            if c != last and c.isalpha():
                                res.append(c)
                                last = c
                        return "".join(res)

                    q_code = _phonetic(query)
                    
                    if len(q_code) >= 2: # Only if we have a valid code
                        # We reuse all_products from Fallback 2 if available, else fetch
                        if 'all_products' not in locals():
                             all_products_q = session.query(BusinessOffering.id, BusinessOffering.name).filter(BusinessOffering.tenant_id == tenant_id)
                             all_products = all_products_q.all()

                        # Scan all products for phonetic match
                        # We allow CONTAINMENT (e.g. "Sakal" code in "Sakal Tirasi" code)
                        matches = []
                        for pid, name in all_products:
                            p_code = _phonetic(name)
                            if q_code == p_code or (len(q_code) > 2 and q_code in p_code) or (len(p_code) > 2 and p_code in q_code):
                                matches.append(pid)
                                if len(matches) >= limit: break
                        
                        if matches:
                            results = session.query(BusinessOffering).filter(BusinessOffering.id.in_(matches)).all()
                            
                except Exception as ex:
                    print(f"Phonetic Logic Error: {ex}")
            # -------------------------------------------------------
            
            # Map DB to Domain
            for item in results:
                # Formatting price
                currency_symbol = "₺" if item.currency == "TRY" else "$"
                
                prod = Product(
                    id=str(item.id),
                    name=item.name,
                    price=item.price if item.price else 0.0,
                    currency=item.currency,
                    is_in_stock=True if item.stock is None or item.stock > 0 else False,
                    description=f"{item.category}: {item.description or ''} | {item.price}{currency_symbol}",
                    category=item.category or "General"
                )
                products.append(prod)
                
            return products
        except Exception as e:
            print(f"Repository Search Error: {e}")
            return []
        finally:
            session.close()

    def list_all_products(self, limit: int = 10, tenant_id: Optional[str] = None) -> List[Product]:
        """
        Returns a sample of products for catalog queries.
        """
        return self.search_products(query=None, limit=limit, tenant_id=tenant_id)

    def get_catalog_summary(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns a rich summary of catalogue (Categories + Price Ranges).
        """
        session = self.get_session()
        try:
            if not tenant_id:
                return []
            
            # Select category, count, min_price, max_price, currency
            query = session.query(
                BusinessOffering.category,
                func.count(BusinessOffering.id),
                func.min(BusinessOffering.price),
                func.max(BusinessOffering.price),
                BusinessOffering.currency
            ).filter(
                BusinessOffering.tenant_id == tenant_id
            ).group_by(
                BusinessOffering.category
            ).all()
            
            summary = []
            for row in query:
                # SQLAlchemy < 1.4 row access might differ, but unpacking tuple usually safe
                cat, count, min_p, max_p, curr = row
                if not cat: continue # Skip None categories
                
                summary.append({
                    "category": cat,
                    "count": count,
                    "min": float(min_p) if min_p else 0.0,
                    "max": float(max_p) if max_p else 0.0,
                    "currency": curr or "USD"
                })
            return summary
        except Exception as e:
            print(f"Repository Catalog Summary Error: {e}")
            return []
        finally:
            session.close()

    def get_safe_schema_summary(self) -> str:
        return "BusinessOfferings(tenant_id, name, price, category, description)"

    def log_call(self, customer_text: str, ai_response: str, sentiment: str, summary: str, intent: Optional[str] = None):
        session = self.get_session()
        try:
            log_entry = CallLog(
                customer_text=customer_text,
                ai_response=ai_response,
                sentiment=sentiment,
                summary=summary,
                intent=intent
            )
            session.add(log_entry)
            session.commit()
        except Exception as e:
            print(f"Repository Logging Error: {e}")
        finally:
            session.close()

    def get_tenant_info(self, tenant_id: str) -> Dict[str, Any]:
        """
        Queries company_info table.
        """
        session = self.get_session()
        try:
            # 1. Get Name
            name_row = session.execute(
                text("SELECT val FROM company_info_view WHERE tid=:tid AND key='ad'"), # Fake view, using raw table below
                {"tid": tenant_id}
            ).fetchone()
            
            # Actually let's use the ORM or raw SQL on new table
            results = session.query(CompanyInfo).filter_by(tenant_id=tenant_id).all()
            info = {}
            for row in results:
                info[row.topic_key] = row.content
                
            return info
        except Exception:
            return {}
        finally:
            session.close()
