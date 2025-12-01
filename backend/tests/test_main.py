import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.main import app
from app.database import Base, get_db
from app.websockets import manager
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

# Wczytanie zmiennych srodowiskowych z .env
load_dotenv()

# Uzycie tej samej bazy co aplikacja (testy tworza i usuwaja tabele)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/stockguard_db")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DATABASE_URL)


@pytest.fixture
async def db_engine():
    """
    Fixture tworzacy izolowany silnik bazy danych dla kazdego testu.
    """
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """
    Fixture tworzacy sesje bazy danych dla testu.
    """
    TestingSessionLocal = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def override_db(db_session):
    """
    Fixture nadpisujacy zaleznosc get_db dla testow.
    """
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_product(override_db) -> None:
    """
    Test tworzenia nowego produktu przez endpoint POST /products/.

    Sprawdza czy produkt jest poprawnie tworzony i czy zwrocona odpowiedz
    zawiera wszystkie wymagane dane oraz przypisane ID.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/products/", json={
            "name": "Test Product",
            "price": 10.5,
            "quantity": 100,
            "low_stock_threshold": 10
        })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert "id" in data

@pytest.mark.asyncio
async def test_update_product_triggers_alert(override_db) -> None:
    """
    Test aktualizacji produktu i wyzwalania alertu niskiego stanu magazynowego.

    Sprawdza czy przy aktualizacji ilosci ponizej progu (low_stock_threshold)
    system poprawnie wysyla alert WebSocket do podlaczonych klientow.
    """
    from unittest.mock import AsyncMock, patch
    
    with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Tworzenie Produktu
            create_res = await ac.post("/products/", json={
                "name": "Alert Product",
                "price": 20.0,
                "quantity": 10,
                "low_stock_threshold": 5
            })
            product_id = create_res.json()["id"]

            # 2. Aktualizacja produktu zeby wywolac alert (quantity 3 < threshold 5)
            update_res = await ac.put(f"/products/{product_id}", json={
                "quantity": 3
            })
            
            assert update_res.status_code == 200
            assert update_res.json()["quantity"] == 3
            
            # 3. Weryfikacja czy alert zostal wyslany przez WebSocket
            alert_called = False
            for call in mock_broadcast.call_args_list:
                args = call[0][0]
                if args.get("type") == "alert" and "Alert Product" in args.get("message", ""):
                    alert_called = True
                    break
            
            assert alert_called, "Alert broadcast was not sent"

@pytest.mark.asyncio
async def test_read_products_list(override_db) -> None:
    """
    Test pobierania listy produktow przez endpoint GET /products/.

    Sprawdza czy endpoint poprawnie zwraca liste produktow
    oraz czy nowo utworzony produkt pojawia sie w tej liscie.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/products/", json={
            "name": "List Product",
            "price": 10.0,
            "quantity": 50,
            "low_stock_threshold": 5
        })
        
        response = await ac.get("/products/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        names = [p["name"] for p in data]
        assert "List Product" in names

@pytest.mark.asyncio
async def test_read_single_product(override_db) -> None:
    """
    Test pobierania pojedynczego produktu przez endpoint GET /products/{id}.

    Sprawdza czy endpoint poprawnie zwraca dane konkretnego produktu
    na podstawie jego ID.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post("/products/", json={
            "name": "Single Product",
            "price": 15.0,
            "quantity": 20,
            "low_stock_threshold": 5
        })
        product_id = create_res.json()["id"]

        response = await ac.get(f"/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Single Product"
        assert data["id"] == product_id

@pytest.mark.asyncio
async def test_read_product_not_found(override_db) -> None:
    """
    Test obslugi bledu 404 dla nieistniejacego produktu.

    Sprawdza czy endpoint zwraca kod 404 i odpowiedni komunikat
    gdy probujemy pobrac produkt o nieistniejacym ID.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/products/999999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"

@pytest.mark.asyncio
async def test_delete_product(override_db) -> None:
    """
    Test usuwania produktu przez endpoint DELETE /products/{id}.

    Sprawdza czy produkt jest poprawnie usuwany i czy po usunieciu
    nie jest juz dostepny w systemie (zwraca 404).
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post("/products/", json={
            "name": "To Delete",
            "price": 5.0,
            "quantity": 10,
            "low_stock_threshold": 5
        })
        product_id = create_res.json()["id"]

        del_res = await ac.delete(f"/products/{product_id}")
        assert del_res.status_code == 200

        get_res = await ac.get(f"/products/{product_id}")
        assert get_res.status_code == 404
