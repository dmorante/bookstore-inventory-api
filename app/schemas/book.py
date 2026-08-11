"""
Esquemas de entrada/salida para el recurso `Book`.

Aprovechamos `SQLModel` (que es también un `BaseModel` de Pydantic) para
compartir los campos con el modelo de tabla vía `BookBase`:

- `BookCreate`: hereda tal cual de `BookBase` (mismos campos + validaciones).
- `BookUpdate`: todos los campos opcionales; se aplican validaciones solo
  a los que vengan informados.
- `BookRead`: `BookBase` + campos generados por el servidor.

Los esquemas de respuestas compuestas (paginación y cálculo de precio)
se mantienen como `BaseModel` de Pydantic puro por simplicidad.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Field, SQLModel

from app.models.book import BookBase, validate_country, validate_isbn
from pydantic import field_validator


# ---------------------------------------------------------------------------
# Esquemas de request
# ---------------------------------------------------------------------------


class BookCreate(BookBase):
    """Payload para crear un libro (`POST /books`)."""


class BookUpdate(SQLModel):
    """
    Payload para actualizar un libro (`PUT /books/{id}`).

    Todos los campos son opcionales: solo se actualizan los enviados.
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    author: Optional[str] = Field(default=None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    cost_usd: Optional[float] = Field(default=None, gt=0)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    supplier_country: Optional[str] = Field(default=None, min_length=2, max_length=2)

    @field_validator("isbn")
    @classmethod
    def _isbn(cls, v: Optional[str]) -> Optional[str]:
        return validate_isbn(v) if v is not None else None

    @field_validator("supplier_country")
    @classmethod
    def _country(cls, v: Optional[str]) -> Optional[str]:
        return validate_country(v) if v is not None else None


# ---------------------------------------------------------------------------
# Esquemas de response
# ---------------------------------------------------------------------------


class BookRead(BookBase):
    """Representación de un libro devuelta por la API."""

    id: int
    selling_price_local: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class PaginatedBooks(BaseModel):
    """Respuesta paginada para `GET /books`."""

    items: list[BookRead]
    total: int = PydanticField(description="Total de libros que cumplen la consulta.")
    skip: int = PydanticField(description="Cantidad de registros omitidos (offset).")
    limit: int = PydanticField(description="Tamaño de la página solicitada.")


class PriceCalculation(BaseModel):
    """Respuesta detallada del cálculo de precio."""

    book_id: int = PydanticField(examples=[1])
    cost_usd: float = PydanticField(examples=[15.99])
    exchange_rate: float = PydanticField(description="Tasa de cambio USD → moneda local aplicada.", examples=[0.85])
    cost_local: float = PydanticField(description="Costo del libro convertido a moneda local.", examples=[13.59])
    margin_percentage: float = PydanticField(description="Margen de ganancia aplicado (%).", examples=[40])
    selling_price_local: float = PydanticField(description="Precio de venta sugerido en moneda local.", examples=[19.03])
    currency: str = PydanticField(description="Código ISO 4217 de la moneda local.", examples=["EUR"])
    calculation_timestamp: datetime = PydanticField(description="Momento (UTC) en que se realizó el cálculo.")
    used_fallback_rate: bool = PydanticField(
        default=False,
        description="Indica si se usó la tasa por defecto porque la API externa falló.",
    )
