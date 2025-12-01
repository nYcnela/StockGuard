# StockGuard

System zarzadzania magazynem z monitorowaniem w czasie rzeczywistym.

## O projekcie

StockGuard to aplikacja webowa do zarzadzania produktami w magazynie. Umozliwia dodawanie, edytowanie i usuwanie produktow, a takze monitorowanie stanow magazynowych w czasie rzeczywistym przez WebSocket.

Gdy ilosc produktu spadnie ponizej ustawionego progu, system automatycznie wysyla alert.

## Funkcjonalnosci

- **CRUD produktow** - dodawanie, edycja, usuwanie i przegladanie produktow
- **Monitorowanie w czasie rzeczywistym** - WebSocket przesyla aktualizacje do wszystkich polaczonych klientow
- **Alerty niskiego stanu** - automatyczne powiadomienia gdy ilosc produktu spadnie ponizej progu
- **Status serwera** - ciagle monitorowanie stanu backendu (co 5 sekund)
- **Responsywny interfejs** - frontend dostosowany do roznych rozmiarow ekranu
- **Dokumentacja API** - automatycznie generowana przez Swagger UI i ReDoc

## Wymagania

Zalecane uruchomienie przez **Docker** - wystarczy miec zainstalowany Docker i Docker Compose.

Przy uruchomieniu lokalnym projekt byl testowany na:

- Python 3.12
- Node.js 23.10
- PostgreSQL 17

Powinno dzialac od:

- Python 3.10+
- Node.js 18.17+
- PostgreSQL 13+

## Technologie

**Backend:**

- FastAPI + SQLAlchemy (async)
- PostgreSQL
- WebSocket

**Frontend:**

- Next.js 16 + React 19
- TypeScript
- Tailwind CSS

## Struktura projektu

```
StockGuard/
├── backend/
│   ├── app/
│   │   ├── main.py          # Aplikacja FastAPI, endpointy REST i WebSocket
│   │   ├── database.py      # Polaczenie z baza danych
│   │   ├── models.py        # Model Product (SQLAlchemy)
│   │   ├── schemas.py       # Schematy Pydantic
│   │   └── websockets.py    # Obsluga WebSocket
│   ├── tests/               # Testy pytest
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                 # Konfiguracja bazy danych
│
├── frontend/
│   ├── app/
│   │   ├── globals.css      # Globalne style CSS
│   │   ├── layout.tsx       # Glowny layout aplikacji
│   │   └── page.tsx         # Strona glowna z logika CRUD
│   ├── public/              # Pliki statyczne
│   ├── Dockerfile
│   ├── next.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.local           # Adresy API i WebSocket
│
├── docker-compose.yml
└── README.md
```

## Uruchomienie

### Klonowanie repozytorium

```bash
git clone https://github.com/nYcnela/StockGuard.git
cd StockGuard
```

### Opcja 1: Docker (zalecane)

```bash
docker compose up --build
```

Aplikacja bedzie dostepna:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Dokumentacja API: http://localhost:8000/docs

### Opcja 2: Lokalnie

Wymaga zainstalowanego Python, Node.js i PostgreSQL.

**Przygotowanie bazy danych:**

1. Utworz baze danych `stockguard_db` w PostgreSQL
2. Skonfiguruj plik `backend/.env` z danymi dostepu do bazy:

```env
DATABASE_URL=postgresql+asyncpg://UZYTKOWNIK:HASLO_DO_BAZY@localhost:5432/stockguard_db
```

**Backend:**

```bash
cd backend

# Utworzenie srodowiska wirtualnego
python -m venv .venv

# Aktywacja srodowiska
.venv\Scripts\activate     # Windows
# lub
source .venv/bin/activate  # Linux / macOS

# Instalacja zaleznosci i uruchomienie
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend (w nowym terminalu):**

```bash
cd frontend
npm install
npm run dev
```

Aplikacja bedzie dostepna:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## API

| Metoda | Endpoint         | Opis                                |
| ------ | ---------------- | ----------------------------------- |
| GET    | `/products/`     | Lista produktow                     |
| POST   | `/products/`     | Dodaj produkt                       |
| GET    | `/products/{id}` | Pobierz produkt                     |
| PUT    | `/products/{id}` | Aktualizuj produkt                  |
| DELETE | `/products/{id}` | Usun produkt                        |
| WS     | `/ws`            | WebSocket - status serwera i alerty |

## Testy

### Lokalnie

Testy korzystaja z tej samej bazy danych co aplikacja (`stockguard_db`). Przed kazdym testem tabele sa tworzone, a po tescie usuwane.

```bash
cd backend
pytest -v
```

### Docker

Komendy wykonujemy w katalogu projektu (gdzie jest `docker-compose.yml`).

Jesli kontenery sa uruchomione (`docker compose up`):

```bash
docker compose exec backend pytest -v
```

Jesli kontenery sa zbudowane, ale nie uruchomione:

```bash
docker compose run --rm backend pytest -v
```
