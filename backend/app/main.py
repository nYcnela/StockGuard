from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
import asyncio

from app.database import engine, Base, get_db
from app.models import Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.websockets import manager, broadcast_server_status

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Menedzer kontekstu cyklu zycia aplikacji obslugujacy zdarzenia startu i zamkniecia.

    Uruchamia zadanie w tle do rozglaszania statusu serwera oraz inicjalizuje tabele bazy danych.
    Po zamknieciu aplikacji anuluje zadania w tle.

    Args:
        app: Instancja aplikacji FastAPI.

    Yields:
        None: Przekazuje kontrole do aplikacji podczas jej dzialania.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    task = asyncio.create_task(broadcast_server_status())
    
    yield

    task.cancel()

app = FastAPI(lifespan=lifespan, title="StockGuard API")

#Cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#endpointy
@app.post("/products/", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)) -> ProductResponse:
    """
    Tworzy nowy produkt w bazie danych.
    
    Args:
        product: Dane nowego produktu.
        db: Sesja bazy danych.
    
    Returns:
        ProductResponse: Utworzony produkt z przypisanym ID.
    """
    new_product = Product(**product.model_dump())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    await manager.broadcast({
        "type": "product_created",
        "product": {
            "id": new_product.id,
            "name": new_product.name,
            "description": new_product.description,
            "price": new_product.price,
            "quantity": new_product.quantity,
            "low_stock_threshold": new_product.low_stock_threshold
        }
    })

    return new_product

@app.get("/products/", response_model=list[ProductResponse])
async def read_products(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[ProductResponse]:
    """
    Pobiera liste produktow z paginacja.
    
    Args:
        skip: Liczba produktow do pominiecia (domyslnie 0).
        limit: Maksymalna liczba produktow do zwrocenia (domyslnie 100).
        db: Sesja bazy danych.
    
    Returns:
        list[ProductResponse]: Lista produktow.
    """
    result = await db.execute(select(Product).offset(skip).limit(limit))
    products = result.scalars().all()
    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)) -> ProductResponse:
    """
    Pobiera konkretny produkt po ID.
    
    Args:
        product_id: ID produktu do pobrania.
        db: Sesja bazy danych.
    
    Returns:
        ProductResponse: Dane produktu.
    
    Raises:
        HTTPException: Gdy produkt o podanym ID nie istnieje (404).
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product_update: ProductUpdate, db: AsyncSession = Depends(get_db)) -> ProductResponse:
    """
    Aktualizuje produkt. Wysyla alert WebSocket, gdy ilosc spadnie ponizej progu.
    
    Args:
        product_id: ID produktu do aktualizacji.
        product_update: Dane do aktualizacji.
        db: Sesja bazy danych.
    
    Returns:
        ProductResponse: Zaktualizowany produkt.
    
    Raises:
        HTTPException: Gdy produkt o podanym ID nie istnieje (404).
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)

    # Rozgloszenie aktualizacji
    await manager.broadcast({
        "type": "product_updated",
        "product": {
            "id": db_product.id,
            "name": db_product.name,
            "description": db_product.description,
            "price": db_product.price,
            "quantity": db_product.quantity,
            "low_stock_threshold": db_product.low_stock_threshold
        }
    })

    # Sprawdzenie alertu niskiego stanu magazynowego
    if db_product.quantity < db_product.low_stock_threshold:
        await manager.broadcast({
            "type": "alert",
            "product": db_product.name,
            "message": f"Niski stan magazynowy produktu: {db_product.name} (Ilość: {db_product.quantity})"
        })

    return db_product

@app.delete("/products/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Usuwa produkt po ID.
    
    Args:
        product_id: ID produktu do usuniecia.
        db: Sesja bazy danych.
    
    Returns:
        dict: Potwierdzenie pomyslnego usuniecia.
    
    Raises:
        HTTPException: Gdy produkt o podanym ID nie istnieje (404).
    """
    result = await db.execute(select(Product).filter(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_id_copy = db_product.id
    await db.delete(db_product)
    await db.commit()

    await manager.broadcast({
        "type": "product_deleted",
        "product_id": product_id_copy
    })

    return {"ok": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Endpoint WebSocket do komunikacji w czasie rzeczywistym.
    
    Obsluguje polaczenia WebSocket dla aktualizacji w czasie rzeczywistym, w tym:
    - Rozglaszanie statusu serwera co 5 sekund
    - Powiadomienia o operacjach CRUD na produktach
    - Alerty niskiego stanu magazynowego
    
    Args:
        websocket: Instancja polaczenia WebSocket.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
