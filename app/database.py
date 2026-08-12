"""
Configuración de la conexión a base de datos usando SQLModel (async).

SQLModel se apoya en SQLAlchemy 2.0, por lo que reutilizamos
`create_async_engine` para el motor. La sesión, en cambio, la tomamos
de `sqlmodel.ext.asyncio.session.AsyncSession` porque expone el método
`exec()` optimizado para consultas SQLModel (devuelve directamente
instancias del modelo en lugar de tuplas Row).

Expone:
- `engine`: motor async global (una única instancia por proceso).
- `AsyncSessionLocal`: fábrica de sesiones asíncronas.
- `get_db`: dependencia de FastAPI que entrega una sesión por request y
  la cierra al finalizar.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

settings = get_settings()

# Nota sobre pgbouncer / Supabase Transaction Pooler:
# El transaction pooler (puerto 6543) reasigna conexiones a cada
# transacción, por lo que los prepared statements que asyncpg cachea
# terminan colisionando entre sesiones ("prepared statement already
# exists"). Para funcionar detrás de pgbouncer transaction mode:
#   1. statement_cache_size=0 → asyncpg no cachea prepared statements.
#   2. NullPool → SQLAlchemy no mantiene conexiones abiertas; pgbouncer
#      ya se encarga del pooling del lado del servidor.
# Con conexiones directas (sin pooler) estas opciones tampoco hacen
# daño, solo eliminan una capa de cache local.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI: entrega una sesión async por request.

    La sesión se cierra automáticamente al terminar la petición, tanto
    si el endpoint retorna con éxito como si lanza una excepción.
    """
    async with AsyncSessionLocal() as session:
        yield session
