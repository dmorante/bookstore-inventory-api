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
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Compatibilidad con PgBouncer (Supabase Transaction Pooler, puerto 6543)
# ---------------------------------------------------------------------------
#
# El transaction pooler reasigna la conexión física a cada transacción, así
# que dos sesiones distintas pueden acabar compartiendo backend. Eso rompe
# los prepared statements, que son estado por conexión. Hacen falta tres
# ajustes complementarios:
#
#   1. `statement_cache_size=0` → asyncpg no cachea prepared statements.
#   2. `prepared_statement_cache_size=0` → el dialecto asyncpg de SQLAlchemy
#      tiene su propia capa de cache, independiente de la anterior.
#   3. `prepared_statement_name_func` → aunque no se cacheen, asyncpg sigue
#      creando statements con nombres correlativos (`__asyncpg_stmt_1__`,
#      `_2_`, ...) que colisionan entre conexiones multiplexadas. Generamos
#      un nombre único por statement para evitarlo.
#
# Los tres son argumentos DBAPI: van dentro de `connect_args`, no como
# kwargs de `create_async_engine`.
#
# Además usamos `NullPool`: PgBouncer ya hace el pooling del lado servidor,
# y mantener un segundo pool encima acumula statements inútiles.
#
# Contra una conexión directa (sin pooler) estos ajustes son inocuos: solo
# eliminan una capa de cache local.
CONNECT_ARGS: dict = {
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=NullPool,
    connect_args=CONNECT_ARGS,
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
