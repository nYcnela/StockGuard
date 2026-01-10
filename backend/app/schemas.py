from pydantic import BaseModel, ConfigDict
from typing import Optional, List


# --- Schematy Kategorii ---

class CategoryBase(BaseModel):
    """
    Bazowy model Pydantic dla wspolnych atrybutow kategorii.
    
    Attributes:
        name: Nazwa kategorii.
        description: Opcjonalny opis kategorii.
    """
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    """
    Schemat do tworzenia nowej kategorii.
    Dziedziczy wszystkie pola z CategoryBase.
    """
    pass


class CategoryUpdate(BaseModel):
    """
    Schemat do aktualizacji istniejacej kategorii. Wszystkie pola sa opcjonalne.
    
    Attributes:
        name: Nowa nazwa kategorii.
        description: Nowy opis kategorii.
    """
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    """
    Schemat do zwracania danych kategorii, zawiera ID.
    
    Attributes:
        id: Unikalny identyfikator kategorii.
    """
    id: int

    model_config = ConfigDict(from_attributes=True)


# --- Schematy Produktu ---

class ProductBase(BaseModel):
    """
    Bazowy model Pydantic dla wspolnych atrybutow produktu.
    
    Attributes:
        name: Nazwa produktu.
        description: Opcjonalny opis produktu.
        price: Cena produktu.
        quantity: Ilosc produktu.
        low_stock_threshold: Prog niskiego stanu magazynowego.
        category_id: Opcjonalny identyfikator kategorii produktu.
    """
    name: str
    description: Optional[str] = None
    price: float
    quantity: int
    low_stock_threshold: int = 5
    category_id: Optional[int] = None


class ProductCreate(ProductBase):
    """
    Schemat do tworzenia nowego produktu.
    Dziedziczy wszystkie pola z ProductBase.
    """
    pass


class ProductUpdate(BaseModel):
    """
    Schemat do aktualizacji istniejacego produktu. Wszystkie pola sa opcjonalne.
    
    Attributes:
        name: Nowa nazwa produktu.
        description: Nowy opis produktu.
        price: Nowa cena produktu.
        quantity: Nowa ilosc produktu.
        low_stock_threshold: Nowy prog niskiego stanu magazynowego.
        category_id: Nowy identyfikator kategorii produktu.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    category_id: Optional[int] = None


class ProductResponse(ProductBase):
    """
    Schemat do zwracania danych produktu, zawiera ID oraz opcjonalnie dane kategorii.
    
    Attributes:
        id: Unikalny identyfikator produktu.
        category: Opcjonalne dane kategorii produktu.
    """
    id: int
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)

