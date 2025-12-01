"""
Testy importowania modulow aplikacji.

Sprawdza czy wszystkie glowne moduly aplikacji moga byc poprawnie zaimportowane.
"""


def test_import_app() -> None:
    """
    Test importowania glownej aplikacji FastAPI.

    Sprawdza czy modul app.main moze byc poprawnie zaimportowany
    i czy instancja aplikacji jest dostepna.
    """
    from app.main import app
    assert app is not None


def test_import_models() -> None:
    """
    Test importowania modeli SQLAlchemy.

    Sprawdza czy modul app.models moze byc poprawnie zaimportowany
    i czy klasa Product jest dostepna.
    """
    from app.models import Product
    assert Product is not None


def test_import_schemas() -> None:
    """
    Test importowania schematow Pydantic.

    Sprawdza czy modul app.schemas moze byc poprawnie zaimportowany
    i czy wszystkie schematy sa dostepne.
    """
    from app.schemas import ProductCreate, ProductUpdate, ProductResponse
    assert ProductCreate is not None
    assert ProductUpdate is not None
    assert ProductResponse is not None


def test_import_websockets() -> None:
    """
    Test importowania menedzera WebSocket.

    Sprawdza czy modul app.websockets moze byc poprawnie zaimportowany
    i czy ConnectionManager jest dostepny.
    """
    from app.websockets import ConnectionManager, manager
    assert ConnectionManager is not None
    assert manager is not None

