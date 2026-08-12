# Bookstore Inventory API

API REST para la gestión del inventario de una cadena de librerías, con validación de precios en tiempo real contra una API de tasas de cambio.

Construida con **FastAPI + SQLModel (async) + PostgreSQL**, empaquetada con **Docker** y migraciones con **Alembic**.

> Nota: la prueba pide preferentemente Django. Se acordó con el equipo evaluador realizarla en FastAPI.

## API desplegada

| | |
|---|---|
| **URL base** | <https://bookstore-inventory-api-ldhf.onrender.com> |
| **Swagger UI** | <https://bookstore-inventory-api-ldhf.onrender.com/docs> |
| **ReDoc** | <https://bookstore-inventory-api-ldhf.onrender.com/redoc> |

Desplegada en **Render** (contenedor Docker) contra una base de datos **PostgreSQL gestionada en Supabase**. La colección de Postman incluida ya apunta a esta URL, así que puede probarse sin ejecutar nada en local.

> El plan gratuito de Render suspende el servicio tras un rato sin tráfico: la primera petición puede tardar ~30 s mientras despierta, las siguientes son inmediatas.

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

- `db` — PostgreSQL 16, expuesto en `localhost:5434` (se usa 5434 en el host para no chocar con otros Postgres locales; dentro de la red de Docker sigue siendo `db:5432`).
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

Se incluye [`postman_collection.json`](postman_collection.json) en la raíz. Impórtala en Postman: la variable `baseUrl` ya apunta a la **API desplegada**, por lo que las peticiones funcionan sin levantar nada en local. Para probar contra local, basta con cambiar `baseUrl` a `http://localhost:8000`.

La petición _Books - Create_ guarda automáticamente el ID del libro creado en la variable `bookId`, de modo que las peticiones por ID (get, update, delete, calculate-price) apuntan a un libro válido si se ejecuta esa primero.

La colección incluye además dos peticiones de ejemplo de manejo de errores (422 por validaciones y 404 por libro inexistente).

---

## Despliegue en la nube

El proyecto está desplegado con **Supabase** (base de datos gestionada) y **Render** (API contenedorizada).

### Base de datos — Supabase

1. Crear un proyecto en [Supabase](https://supabase.com).
2. Copiar la connection string del **Transaction Pooler** (puerto 6543).
3. Adaptarla: cambiar el esquema `postgresql://` por `postgresql+asyncpg://` y sustituir la contraseña.

### API — Render

1. **New → Web Service**, conectando este repositorio.
2. **Runtime: Docker** (Render detecta el `Dockerfile` de la raíz).
3. Definir las variables de entorno de la tabla de arriba, con `DATABASE_URL` apuntando a Supabase.

Las migraciones se aplican solas: el `CMD` del Dockerfile ejecuta `alembic upgrade head` antes de arrancar Uvicorn. El servidor escucha en `$PORT` si el proveedor la define, y en 8000 en local.

### Nota técnica: PgBouncer y prepared statements

El Transaction Pooler de Supabase es PgBouncer en modo *transaction*, que reasigna la conexión física en cada transacción. Eso rompe los *prepared statements*, que son estado por conexión, con el error `DuplicatePreparedStatementError`.

La configuración necesaria está en [`app/database.py`](app/database.py) (`CONNECT_ARGS`) y consiste en tres ajustes complementarios —desactivar el cache de asyncpg, desactivar el del dialecto de SQLAlchemy, y generar nombres únicos por statement— más el uso de `NullPool`, ya que el pooling lo hace PgBouncer. Alembic importa esa misma configuración para conectarse igual que la aplicación.

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
