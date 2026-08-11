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
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
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
