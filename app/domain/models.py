from pydantic import BaseModel, Field
from typing import Optional

class Product(BaseModel):
    """
    Universal Domain Model for Store Products.
    Decouples the upper layers from database specifics.
    """
    id: str = Field(..., description="Unique identifier for the product")
    name: str = Field(..., description="Name of the product (Track, Album, etc.)")
    price: float = Field(..., description="Price of the product")
    currency: str = Field(default="USD", description="Currency code")
    is_in_stock: bool = Field(default=True, description="Availability status")
    description: str = Field(..., description="Rich text description including artist, album, genre, etc.")
    
    # Metadata for AI reasoning (optional but helpful)
    category: Optional[str] = Field(None, description="Type: Track, Album, Merch")
    
    def to_context_string(self) -> str:
        """Returns a string representation optimized for AI context."""
        return f"Product: {self.name} | Price: {self.price} {self.currency} | Details: {self.description}"
