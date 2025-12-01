from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProductBase(BaseModel):
    """
    Bazowy model Pydantic dla wspolnych atrybutow produktu.
    
    Attributes:
        name: Nazwa produktu.
        description: Opcjonalny opis produktu.
        price: Cena produktu.
        quantity: Ilosc produktu.
        low_stock_threshold: Prog niskiego stanu magazynowego.
    """
    name: str
    description: Optional[str] = None
    price: float
    quantity: int
    low_stock_threshold: int = 5

class ProductCreate(ProductBase):
    """
    Schemat do tworzenia nowego produktu.
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
    """
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None

class ProductResponse(ProductBase):
    """
    Schemat do zwracania danych produktu, zawiera ID.
    
    Attributes:
        id: Unikalny identyfikator produktu.
    """
    id: int

    model_config = ConfigDict(from_attributes=True)

