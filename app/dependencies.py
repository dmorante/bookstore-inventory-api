"""
Dependencias reutilizables para los endpoints.

Se agrupan aquí para que los routers queden concisos y para que sea
trivial sustituirlas en tests con `app.dependency_overrides`.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.services.book_service import BookService
from app.services.exchange_service import ExchangeRateService


def get_exchange_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExchangeRateService:
    """Provee una instancia del cliente de la API de tasas de cambio."""
    return ExchangeRateService(settings)


def get_book_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    exchange: Annotated[ExchangeRateService, Depends(get_exchange_service)],
) -> BookService:
    """Provee el servicio de libros ya cableado con sus dependencias."""
    return BookService(db=db, settings=settings, exchange_service=exchange)
