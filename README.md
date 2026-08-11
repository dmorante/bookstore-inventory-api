# Bookstore Inventory API

API REST para la gestión del inventario de una cadena de librerías, con validación de precios en tiempo real contra una API de tasas de cambio.

Construida con **FastAPI + SQLModel (async) + PostgreSQL**, empaquetada con **Docker** y migraciones con **Alembic**.

> Nota: la prueba pide preferentemente Django. Se acordó con el equipo evaluador realizarla en FastAPI.

---

## Requisitos previos

- [Docker](https://www.docker.com/) y Docker Compose (opción recomendada), **o**
- Python 3.12+ y una instancia de PostgreSQL 14+ accesible.

---

## Ejecución con Docker (recomendado)

```bash
docker compose up --build
```

Esto levanta:

- `db` — PostgreSQL 16 en `localhost:5432`.
- `api` — la API en `http://localhost:8000` (aplica migraciones automáticamente al arrancar).

Swagger UI: <http://localhost:8000/docs>
ReDoc: <http://localhost:8000/redoc>

Para detener:

```bash
docker compose down
```

Para borrar también los datos:

```bash
docker compose down -v
```

---

## Ejecución local (sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # ajusta DATABASE_URL si es necesario
alembic upgrade head
uvicorn app.main:app --reload
```

---

## Variables de entorno

Ver [.env.example](.env.example). Las principales:

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | URL SQLAlchemy async a Postgres | `postgresql+asyncpg://postgres:postgres@db:5432/bookstore` |
| `EXCHANGE_API_URL` | Endpoint público de tasas | `https://api.exchangerate-api.com/v4/latest/USD` |
| `EXCHANGE_API_TIMEOUT` | Timeout HTTP en segundos | `5` |
| `DEFAULT_MARGIN_PERCENTAGE` | Margen de ganancia aplicado | `40` |
| `DEFAULT_FALLBACK_RATE` | Tasa a usar si la API externa falla | `0.92` |
| `DEFAULT_FALLBACK_CURRENCY` | Moneda del fallback | `EUR` |

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/books` | Crea un libro |
| GET | `/books` | Lista con paginación (`skip`, `limit`) |
| GET | `/books/{id}` | Detalle |
| PUT | `/books/{id}` | Actualiza (parcial) |
| DELETE | `/books/{id}` | Elimina |
| GET | `/books/search?category=...` | Busca por categoría |
| GET | `/books/low-stock?threshold=10` | Libros con stock bajo |
| POST | `/books/{id}/calculate-price` | Calcula precio de venta sugerido |

### Ejemplos rápidos

Crear un libro:

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "El Quijote",
    "author": "Miguel de Cervantes",
    "isbn": "978-84-376-0494-7",
    "cost_usd": 15.99,
    "stock_quantity": 25,
    "category": "Literatura Clásica",
    "supplier_country": "ES"
  }'
```

Calcular precio de venta:

```bash
curl -X POST http://localhost:8000/books/1/calculate-price
```

Respuesta:

```json
{
  "book_id": 1,
  "cost_usd": 15.99,
  "exchange_rate": 0.92,
  "cost_local": 14.71,
  "margin_percentage": 40,
  "selling_price_local": 20.60,
  "currency": "EUR",
  "calculation_timestamp": "2026-08-11T10:30:00Z",
  "used_fallback_rate": false
}
```

---

## Reglas de negocio

- `cost_usd` > 0.
- `stock_quantity` >= 0.
- `isbn` válido de **10 o 13 dígitos** (guiones permitidos) y **único**.
- `supplier_country` en formato ISO 3166-1 alpha-2 (p. ej. `ES`, `MX`, `US`).
- Al calcular precio, si la API externa falla se usa la tasa por defecto (`DEFAULT_FALLBACK_RATE`) siempre que la moneda destino coincida con `DEFAULT_FALLBACK_CURRENCY`; en caso contrario se responde **503**.
- Errores mapeados: **400** (validación / ISBN duplicado / moneda no soportada), **404** (libro inexistente), **422** (schema), **503** (API externa caída).

---

## Colección de Postman

Se incluye `postman_collection.json` en la raíz. Importa en Postman y ajusta la variable `baseUrl` (por defecto `http://localhost:8000`) para apuntar a la URL pública del despliegue.

---

## Despliegue en la nube

- **Base de datos**: crear proyecto en [Supabase](https://supabase.com), copiar la connection string en formato `postgresql://` y convertirla a `postgresql+asyncpg://...`.
- **API**: se puede desplegar el contenedor en Render, Railway, Fly.io, Cloud Run o similares. Definir la variable `DATABASE_URL` apuntando a Supabase.
- Después del primer deploy, ejecutar migraciones (el `CMD` del Dockerfile ya corre `alembic upgrade head` en cada arranque).

---

## Estructura del proyecto

```
bookstore-inventory-api/
├── app/
│   ├── main.py               # Entry point FastAPI
│   ├── config.py             # Settings (pydantic-settings)
│   ├── database.py           # Motor y sesión SQLModel async
│   ├── dependencies.py       # Dependencias de FastAPI
│   ├── core/
│   │   ├── exceptions.py     # Errores de dominio + handler global
│   │   └── country_currency.py
│   ├── models/book.py        # Modelo SQLModel (tabla + BookBase compartido)
│   ├── schemas/book.py       # Esquemas de request/response (SQLModel + Pydantic)
│   ├── routers/books.py      # Endpoints REST
│   └── services/
│       ├── book_service.py   # Lógica de negocio
│       └── exchange_service.py
├── alembic/                  # Migraciones
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── postman_collection.json
└── README.md
```
