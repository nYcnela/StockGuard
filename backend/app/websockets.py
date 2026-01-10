from fastapi import WebSocket
from typing import List
import json
import asyncio
from datetime import datetime


class ServerStatus:
    """
    Klasa reprezentujaca status serwera z mechanizmem synchronizacji dostepu.
    
    Wykorzystuje asyncio.Lock do zapewnienia bezpiecznego dostepu do wspoldzielonych
    zasobow w srodowisku wielowatkowym/asynchronicznym.
    
    Attributes:
        _lock: Blokada asyncio do synchronizacji dostepu.
        _status: Aktualny status serwera (np. "Online", "Offline").
        _timestamp: Znacznik czasu ostatniej aktualizacji statusu.
        _connected_clients: Liczba podlaczonych klientow WebSocket.
    """
    
    def __init__(self) -> None:
        """
        Inicjalizuje obiekt ServerStatus z domyslnymi wartosciami i blokada.
        """
        self._lock = asyncio.Lock()
        self._status: str = "Online"
        self._timestamp: str = datetime.now().isoformat()
        self._connected_clients: int = 0
    
    async def get_status(self) -> dict:
        """
        Pobiera aktualny status serwera w sposob bezpieczny dla watkow.
        
        Uzywa blokady asyncio.Lock aby zapewnic atomowy odczyt wszystkich pol statusu.
        
        Returns:
            dict: Slownik zawierajacy status, timestamp i liczbe podlaczonych klientow.
        """
        async with self._lock:
            return {
                "type": "status",
                "status": self._status,
                "timestamp": self._timestamp,
                "connected_clients": self._connected_clients
            }
    
    async def update_status(self, status: str) -> None:
        """
        Aktualizuje status serwera w sposob bezpieczny dla watkow.
        
        Uzywa blokady asyncio.Lock aby zapewnic atomowa aktualizacje statusu i timestampa.
        
        Args:
            status: Nowy status serwera do ustawienia.
        """
        async with self._lock:
            self._status = status
            self._timestamp = datetime.now().isoformat()
    
    async def increment_clients(self) -> None:
        """
        Zwieksza licznik podlaczonych klientow w sposob bezpieczny dla watkow.
        
        Uzywa blokady asyncio.Lock aby zapewnic atomowa inkrementacje licznika.
        """
        async with self._lock:
            self._connected_clients += 1
            self._timestamp = datetime.now().isoformat()
    
    async def decrement_clients(self) -> None:
        """
        Zmniejsza licznik podlaczonych klientow w sposob bezpieczny dla watkow.
        
        Uzywa blokady asyncio.Lock aby zapewnic atomowa dekrementacje licznika.
        Licznik nie spadnie ponizej 0.
        """
        async with self._lock:
            self._connected_clients = max(0, self._connected_clients - 1)
            self._timestamp = datetime.now().isoformat()
    
    async def refresh_timestamp(self) -> None:
        """
        Odswieza znacznik czasu statusu bez zmiany innych wartosci.
        
        Uzywa blokady asyncio.Lock aby zapewnic atomowa aktualizacje timestampa.
        """
        async with self._lock:
            self._timestamp = datetime.now().isoformat()


# Globalna instancja statusu serwera z mechanizmem blokad
server_status = ServerStatus()


class ConnectionManager:
    """
    Zarzadza aktywnymi polaczeniami WebSocket i obsluguje rozglaszanie wiadomosci.
    
    Wykorzystuje asyncio.Lock do synchronizacji dostepu do listy polaczen,
    zapewniajac bezpieczenstwo w srodowisku asynchronicznym.
    
    Attributes:
        active_connections: Lista aktualnie aktywnych polaczen WebSocket.
        _lock: Blokada asyncio do synchronizacji dostepu do listy polaczen.
    """
    def __init__(self) -> None:
        """
        Inicjalizuje menedzera polaczen z pusta lista i blokada.
        """
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """
        Akceptuje nowe polaczenie WebSocket i dodaje je do listy w sposob bezpieczny.
        
        Uzywa blokady asyncio.Lock oraz aktualizuje globalny status serwera.
        
        Args:
            websocket: Polaczenie WebSocket do zaakceptowania.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        await server_status.increment_clients()

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Usuwa polaczenie WebSocket z listy w sposob bezpieczny.
        
        Uzywa blokady asyncio.Lock oraz aktualizuje globalny status serwera.
        
        Args:
            websocket: Polaczenie WebSocket do usuniecia.
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        await server_status.decrement_clients()

    async def broadcast(self, message: dict) -> None:
        """
        Wysyla wiadomosc JSON do wszystkich aktywnych polaczen w sposob bezpieczny.
        
        Uzywa blokady asyncio.Lock aby uzyskac kopie listy polaczen przed wysylka.
        
        Args:
            message: Slownik do wyslania jako JSON do wszystkich klientow.
        """
        async with self._lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Obsluga potencjalnych problemow z rozlaczeniem podczas rozglaszania
                pass


manager = ConnectionManager()


async def broadcast_server_status() -> None:
    """
    Zadanie w tle rozglaszajace status serwera co 5 sekund.
    
    Ta funkcja dziala w nieskonczonosc i wysyla wiadomosc o statusie zawierajaca
    aktualny znacznik czasu, status serwera oraz liczbe podlaczonych klientow
    do wszystkich podlaczonych klientow WebSocket.
    
    Wykorzystuje mechanizm blokad poprzez obiekt ServerStatus do bezpiecznego
    odczytu wspoldzielonej zmiennej server_status.
    """
    while True:
        # Odswiezenie timestampa przed pobraniem statusu
        await server_status.refresh_timestamp()
        # Pobranie statusu z uzyciem blokady
        status_message = await server_status.get_status()
        await manager.broadcast(status_message)
        await asyncio.sleep(5)
