"""Modelo ORM `Book` — representación de un libro en el inventario."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Book(Base):
    """
    Libro dentro del inventario.

    Cada libro tiene un costo en USD (moneda de importación) y,
    opcionalmente, un precio de venta en la moneda local calculado a
    partir de la tasa de cambio actual más un margen de ganancia.
    """

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)

    # ISBN único (10 o 13 dígitos, con o sin guiones).
    isbn: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # Costo de importación en dólares estadounidenses. Debe ser > 0.
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Precio de venta en moneda local. Null hasta que se calcula.
    selling_price_local: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Cantidad de unidades en stock. No puede ser negativa.
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # País del proveedor en formato ISO 3166-1 alpha-2 (p. ej. "ES", "MX").
    supplier_country: Mapped[str] = mapped_column(String(2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Book id={self.id} isbn={self.isbn} title={self.title!r}>"
