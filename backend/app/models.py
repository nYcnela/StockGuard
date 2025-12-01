from sqlalchemy import Column, Integer, String, Float
from app.database import Base

class Product(Base):
    """
    Model SQLAlchemy reprezentujacy produkt w magazynie.
    
    Attributes:
        id: Unikalny identyfikator produktu.
        name: Nazwa produktu.
        description: Opcjonalny opis produktu.
        price: Cena produktu.
        quantity: Ilosc produktu w magazynie.
        low_stock_threshold: Prog niskiego stanu magazynowego (domyslnie 5).
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    quantity = Column(Integer)
    low_stock_threshold = Column(Integer, default=5)
