# StockGuard - Frontend

Frontend aplikacji StockGuard zbudowany przy uzyciu Next.js 16 z App Router.

## Technologie

- **Next.js 16** - Framework React z App Router
- **React 19** - Biblioteka UI
- **TypeScript** - Statyczne typowanie
- **Tailwind CSS 4** - Stylowanie
- **Axios** - Klient HTTP do komunikacji z API

## Funkcjonalnosci

- Wyswietlanie listy produktow w magazynie
- Dodawanie nowych produktow
- Edycja istniejacych produktow
- Usuwanie produktow
- Polaczenie WebSocket do aktualizacji w czasie rzeczywistym
- Wyswietlanie statusu serwera
- Alerty o niskim stanie magazynowym

## Uruchomienie

### Wymagania

- Node.js 20+ (zalecane 23.10)
- npm lub yarn

### Instalacja

```bash
npm install
```

### Tryb deweloperski

```bash
npm run dev
```

Aplikacja bedzie dostepna pod adresem [http://localhost:3000](http://localhost:3000).

### Budowanie produkcyjne

```bash
npm run build
npm start
```

## Zmienne srodowiskowe

Utworz plik `.env.local` z nastepujacymi zmiennymi:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Struktura projektu

```
frontend/
├── app/
│   ├── globals.css      # Globalne style CSS
│   ├── layout.tsx       # Glowny layout aplikacji
│   └── page.tsx         # Strona glowna z logika CRUD
├── public/              # Pliki statyczne
├── Dockerfile           # Konfiguracja Docker
├── next.config.ts       # Konfiguracja Next.js
├── package.json         # Zaleznosci projektu
├── tailwind.config.ts   # Konfiguracja Tailwind CSS
└── tsconfig.json        # Konfiguracja TypeScript
```

## Docker

Aby uruchomic frontend w kontenerze Docker:

```bash
docker build -t stockguard-frontend .
docker run -p 3000:3000 stockguard-frontend
```

Lub uzyj docker-compose z glownego katalogu projektu:

```bash
docker compose up frontend
```
