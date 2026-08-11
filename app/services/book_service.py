"""
Lógica de negocio para el recurso `Book`.

Todas las operaciones sobre la base de datos y las reglas de dominio
viven aquí. Los endpoints solo se encargan de:
- Recibir el request.
- Delegar en este servicio.
- Serializar la respuesta.

Usamos la `AsyncSession` de SQLModel, que expone `.exec()` en lugar de
`.execute()`. `exec()` devuelve directamente instancias del modelo
(en vez de tuplas Row), lo que hace el código más legible.
"""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import Settings
from app.core.country_currency import currency_for_country
from app.core.exceptions import (
    BookNotFoundError,
    DuplicateISBNError,
    ExchangeRateUnavailableError,
)
from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate, PriceCalculation
from app.services.exchange_service import ExchangeRateService


class BookService:
    """Servicio de aplicación para gestionar libros."""

    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        exchange_service: ExchangeRateService,
    ) -> None:
        self._db = db
        self._settings = settings
        self._exchange = exchange_service

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, data: BookCreate) -> Book:
        """Crea un nuevo libro. Falla con 400 si el ISBN ya existe."""
        book = Book.model_validate(data)
        self._db.add(book)
        try:
            await self._db.commit()
        except IntegrityError as exc:
            await self._db.rollback()
            raise DuplicateISBNError(
                f"Ya existe un libro con ISBN '{data.isbn}'."
            ) from exc
        await self._db.refresh(book)
        return book

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
    ) -> tuple[list[Book], int]:
        """Lista libros con paginación y filtro opcional por categoría."""
        base_query = select(Book)
        count_query = select(func.count()).select_from(Book)
        if category:
            base_query = base_query.where(Book.category == category)
            count_query = count_query.where(Book.category == category)

        total_result = await self._db.exec(count_query)
        total = total_result.one()

        items_result = await self._db.exec(
            base_query.order_by(Book.id).offset(skip).limit(limit)
        )
        return list(items_result.all()), int(total)

    async def get(self, book_id: int) -> Book:
        """Devuelve un libro por su ID o levanta `BookNotFoundError`."""
        book = await self._db.get(Book, book_id)
        if book is None:
            raise BookNotFoundError(f"No existe un libro con id={book_id}.")
        return book

    async def update(self, book_id: int, data: BookUpdate) -> Book:
        """Actualiza solo los campos enviados en el payload."""
        book = await self.get(book_id)
        changes = data.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(book, key, value)
        self._db.add(book)
        try:
            await self._db.commit()
        except IntegrityError as exc:
            await self._db.rollback()
            raise DuplicateISBNError(
                "Ya existe otro libro con ese ISBN."
            ) from exc
        await self._db.refresh(book)
        return book

    async def delete(self, book_id: int) -> None:
        """Elimina un libro."""
        book = await self.get(book_id)
        await self._db.delete(book)
        await self._db.commit()

    async def low_stock(self, threshold: int) -> list[Book]:
        """Devuelve libros con stock por debajo (o igual) del umbral."""
        result = await self._db.exec(
            select(Book)
            .where(Book.stock_quantity <= threshold)
            .order_by(Book.stock_quantity)
        )
        return list(result.all())

    # ------------------------------------------------------------------
    # Cálculo de precio
    # ------------------------------------------------------------------

    async def calculate_price(self, book_id: int) -> PriceCalculation:
        """
        Calcula el precio de venta sugerido para un libro.

        Pasos:
        1. Recupera el libro por ID.
        2. Deriva la moneda local a partir del `supplier_country`.
        3. Obtiene la tasa de cambio actual desde la API externa (con
           fallback si falla).
        4. Aplica el margen configurado (por defecto 40%).
        5. Persiste el `selling_price_local` calculado.
        6. Retorna el desglose completo del cálculo.
        """
        book = await self.get(book_id)
        currency = currency_for_country(book.supplier_country)

        try:
            rate, used_fallback = await self._exchange.get_rate(currency)
        except RuntimeError as exc:
            raise ExchangeRateUnavailableError(
                f"No se pudo obtener la tasa USD → {currency}."
            ) from exc

        margin = self._settings.default_margin_percentage
        cost_usd = float(book.cost_usd)
        cost_local = round(cost_usd * rate, 2)
        selling_price_local = round(cost_local * (1 + margin / 100), 2)

        book.selling_price_local = selling_price_local
        self._db.add(book)
        await self._db.commit()
        await self._db.refresh(book)

        return PriceCalculation(
            book_id=book.id,
            cost_usd=cost_usd,
            exchange_rate=rate,
            cost_local=cost_local,
            margin_percentage=margin,
            selling_price_local=selling_price_local,
            currency=currency,
            calculation_timestamp=datetime.now(UTC),
            used_fallback_rate=used_fallback,
        )
