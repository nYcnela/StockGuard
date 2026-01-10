from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
import asyncio

from app.database import engine, Base, get_db
from app.models import Product, Category
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    CategoryCreate, CategoryUpdate, CategoryResponse
)
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

#ENDPOINTY KATEGORII

@app.post("/categories/", response_model=CategoryResponse)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)) -> CategoryResponse:
    """
    Tworzy nowa kategorie w bazie danych.
    
    Args:
        category: Dane nowej kategorii.
        db: Sesja bazy danych.
    
    Returns:
        CategoryResponse: Utworzona kategoria z przypisanym ID.
    
    Raises:
        HTTPException: Gdy kategoria o podanej nazwie juz istnieje (400).
    """
    # Sprawdzenie czy kategoria o takiej nazwie juz istnieje
    result = await db.execute(select(Category).filter(Category.name == category.name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    new_category = Category(**category.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    await manager.broadcast({
        "type": "category_created",
        "category": {
            "id": new_category.id,
            "name": new_category.name,
            "description": new_category.description
        }
    })

    return new_category


@app.get("/categories/", response_model=list[CategoryResponse])
async def read_categories(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[CategoryResponse]:
    """
    Pobiera liste kategorii z paginacja.
    
    Args:
        skip: Liczba kategorii do pominiecia (domyslnie 0).
        limit: Maksymalna liczba kategorii do zwrocenia (domyslnie 100).
        db: Sesja bazy danych.
    
    Returns:
        list[CategoryResponse]: Lista kategorii.
    """
    result = await db.execute(select(Category).offset(skip).limit(limit))
    categories = result.scalars().all()
    return categories


@app.get("/categories/{category_id}", response_model=CategoryResponse)
async def read_category(category_id: int, db: AsyncSession = Depends(get_db)) -> CategoryResponse:
    """
    Pobiera konkretna kategorie po ID.
    
    Args:
        category_id: ID kategorii do pobrania.
        db: Sesja bazy danych.
    
    Returns:
        CategoryResponse: Dane kategorii.
    
    Raises:
        HTTPException: Gdy kategoria o podanym ID nie istnieje (404).
    """
    result = await db.execute(select(Category).filter(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@app.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, category_update: CategoryUpdate, db: AsyncSession = Depends(get_db)) -> CategoryResponse:
    """
    Aktualizuje kategorie.
    
    Args:
        category_id: ID kategorii do aktualizacji.
        category_update: Dane do aktualizacji.
        db: Sesja bazy danych.
    
    Returns:
        CategoryResponse: Zaktualizowana kategoria.
    
    Raises:
        HTTPException: Gdy kategoria o podanym ID nie istnieje (404).
        HTTPException: Gdy kategoria o nowej nazwie juz istnieje (400).
    """
    result = await db.execute(select(Category).filter(Category.id == category_id))
    db_category = result.scalar_one_or_none()
    
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = category_update.model_dump(exclude_unset=True)
    
    # Sprawdzenie unikalnosci nazwy jesli jest aktualizowana
    if "name" in update_data and update_data["name"] != db_category.name:
        existing = await db.execute(select(Category).filter(Category.name == update_data["name"]))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    for key, value in update_data.items():
        setattr(db_category, key, value)

    await db.commit()
    await db.refresh(db_category)

    await manager.broadcast({
        "type": "category_updated",
        "category": {
            "id": db_category.id,
            "name": db_category.name,
            "description": db_category.description
        }
    })

    return db_category


@app.delete("/categories/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Usuwa kategorie po ID.
    
    Przed usunieciem ustawia category_id na None dla wszystkich produktow w tej kategorii.
    
    Args:
        category_id: ID kategorii do usuniecia.
        db: Sesja bazy danych.
    
    Returns:
        dict: Potwierdzenie pomyslnego usuniecia.
    
    Raises:
        HTTPException: Gdy kategoria o podanym ID nie istnieje (404).
    """
    result = await db.execute(select(Category).filter(Category.id == category_id))
    db_category = result.scalar_one_or_none()
    
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Usuniecie przypisania kategorii z produktow
    products_result = await db.execute(select(Product).filter(Product.category_id == category_id))
    products = products_result.scalars().all()
    for product in products:
        product.category_id = None
    
    category_id_copy = db_category.id
    await db.delete(db_category)
    await db.commit()

    await manager.broadcast({
        "type": "category_deleted",
        "category_id": category_id_copy
    })

    return {"ok": True}


#ENDPOINTY PRODUKTOW

@app.post("/products/", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)) -> ProductResponse:
    """
    Tworzy nowy produkt w bazie danych.
    
    Args:
        product: Dane nowego produktu.
        db: Sesja bazy danych.
    
    Returns:
        ProductResponse: Utworzony produkt z przypisanym ID.
    
    Raises:
        HTTPException: Gdy podana kategoria nie istnieje (404).
    """
    # Sprawdzenie czy kategoria istnieje (jesli podana)
    if product.category_id:
        cat_result = await db.execute(select(Category).filter(Category.id == product.category_id))
        if cat_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Category not found")
    
    new_product = Product(**product.model_dump())
    db.add(new_product)
    await db.commit()
    
    # Pobranie produktu z zaladowana relacja kategorii
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).filter(Product.id == new_product.id)
    )
    new_product = result.scalar_one()

    await manager.broadcast({
        "type": "product_created",
        "product": {
            "id": new_product.id,
            "name": new_product.name,
            "description": new_product.description,
            "price": new_product.price,
            "quantity": new_product.quantity,
            "low_stock_threshold": new_product.low_stock_threshold,
            "category_id": new_product.category_id,
            "category": {"id": new_product.category.id, "name": new_product.category.name, "description": new_product.category.description} if new_product.category else None
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
        list[ProductResponse]: Lista produktow z danymi kategorii.
    """
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).offset(skip).limit(limit)
    )
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
        ProductResponse: Dane produktu z danymi kategorii.
    
    Raises:
        HTTPException: Gdy produkt o podanym ID nie istnieje (404).
    """
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).filter(Product.id == product_id)
    )
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
        ProductResponse: Zaktualizowany produkt z danymi kategorii.
    
    Raises:
        HTTPException: Gdy produkt o podanym ID nie istnieje (404).
        HTTPException: Gdy podana kategoria nie istnieje (404).
    """
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).filter(Product.id == product_id)
    )
    db_product = result.scalar_one_or_none()
    
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.model_dump(exclude_unset=True)
    
    # Sprawdzenie czy kategoria istnieje (jesli aktualizowana)
    if "category_id" in update_data and update_data["category_id"] is not None:
        cat_result = await db.execute(select(Category).filter(Category.id == update_data["category_id"]))
        if cat_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Category not found")
    
    for key, value in update_data.items():
        setattr(db_product, key, value)

    await db.commit()
    
    # Wyczyszczenie cache i pobranie zaktualizowanego produktu z zaladowana relacja kategorii
    await db.refresh(db_product)
    db.expire(db_product)
    
    result = await db.execute(
        select(Product).options(selectinload(Product.category)).filter(Product.id == product_id)
    )
    db_product = result.scalar_one()

    # Rozgloszenie aktualizacji
    await manager.broadcast({
        "type": "product_updated",
        "product": {
            "id": db_product.id,
            "name": db_product.name,
            "description": db_product.description,
            "price": db_product.price,
            "quantity": db_product.quantity,
            "low_stock_threshold": db_product.low_stock_threshold,
            "category_id": db_product.category_id,
            "category": {"id": db_product.category.id, "name": db_product.category.name, "description": db_product.category.description} if db_product.category else None
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
    - Rozglaszanie statusu serwera co 5 sekund (z uzyciem blokad do synchronizacji)
    - Powiadomienia o operacjach CRUD na produktach i kategoriach
    - Alerty niskiego stanu magazynowego
    - Informacje o liczbie podlaczonych klientow
    
    Args:
        websocket: Instancja polaczenia WebSocket.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
