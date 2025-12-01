from fastapi import WebSocket
from typing import List
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """
    Zarzadza aktywnymi polaczeniami WebSocket i obsluguje rozglaszanie wiadomosci.
    
    Attributes:
        active_connections: Lista aktualnie aktywnych polaczen WebSocket.
    """
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Akceptuje nowe polaczenie WebSocket i dodaje je do listy.
        
        Args:
            websocket: Polaczenie WebSocket do zaakceptowania.
        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Usuwa polaczenie WebSocket z listy.
        
        Args:
            websocket: Polaczenie WebSocket do usuniecia.
        """
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """
        Wysyla wiadomosc JSON do wszystkich aktywnych polaczen.
        
        Args:
            message: Slownik do wyslania jako JSON do wszystkich klientow.
        """
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Obsluga potencjalnych problemow z rozlaczeniem podczas rozglaszania
                pass

manager = ConnectionManager()

async def broadcast_server_status() -> None:
    """
    Zadanie w tle rozglaszajace status serwera i aktualny czas co 5 sekund.
    
    Ta funkcja dziala w nieskonczonosc i wysyla wiadomosc o statusie zawierajaca
    aktualny znacznik czasu i status serwera do wszystkich podlaczonych klientow WebSocket.
    """
    while True:
        message = {
            "type": "status",
            "timestamp": datetime.now().isoformat(),
            "status": "Online"
        }
        await manager.broadcast(message)
        await asyncio.sleep(5)
