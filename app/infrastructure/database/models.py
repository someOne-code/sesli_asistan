from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# ========== INTERNAL TABLES (Analytics) ==========

class CallLog(Base):
    __tablename__ = 'call_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    customer_text = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    
    # New fields for analytics
    duration_seconds = Column(Integer, nullable=True, default=0)
    intent = Column(String(50), nullable=True)
    is_error = Column(Boolean, nullable=True, default=False)
    tenant_id = Column(String(50), nullable=True, index=True) # Added for tenant analytics

# ========== SAAS BUSINESS MODELS (Universal) ==========

class BusinessOffering(Base):
    """
    Universal table for all tenant products & services.
    Replaces legacy Music Store tables (Track, Album, Genre).
    
    Examples:
    - Music Tenant: name="Master of Puppets", category="Music", price=19.99
    - Barber Tenant: name="Saç Kesimi", category="Service", price=200.00
    """
    __tablename__ = 'business_offerings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), nullable=False, index=True) # Partition Key
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True) # e.g. "Hizmet", "Ürün", "Albüm"
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="TRY")
    
    is_active = Column(Boolean, default=True)
    stock = Column(Integer, nullable=True) # None for infinite services
    
    # Search Optimization
    __table_args__ = (
        Index('idx_tenant_search', 'tenant_id', 'name'),
    )

    def __repr__(self):
        return f"Product(name='{self.name}', price={self.price} {self.currency}, category='{self.category}', desc='{self.description}')"

class CompanyInfo(Base):
    """
    Stores tenant metadata (Vision, Address, Contact).
    """
    __tablename__ = 'company_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    topic_key = Column(String(50), nullable=False) # e.g. "vizyon", "adres"
    content = Column(Text, nullable=False)
    locale = Column(String(10), default="tr")
    is_active = Column(Boolean, default=True)
    
class Tenant(Base):
    """
    Master table for tenants (Authentication & Config).
    """
    __tablename__ = 'tenants'
    
    id = Column(String(50), primary_key=True) # Slug (e.g. 'berber_ahmet')
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
