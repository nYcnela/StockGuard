from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    """
    Model SQLAlchemy reprezentujacy kategorie produktow w magazynie.
    
    Attributes:
        id: Unikalny identyfikator kategorii.
        name: Nazwa kategorii.
        description: Opcjonalny opis kategorii.
        products: Lista produktow nalezacych do tej kategorii (relacja).
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(String, nullable=True)
    
    products = relationship("Product", back_populates="category")


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
        category_id: Opcjonalny identyfikator kategorii produktu (klucz obcy).
        category: Relacja do kategorii produktu.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    quantity = Column(Integer)
    low_stock_threshold = Column(Integer, default=5)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    category = relationship("Category", back_populates="products")
