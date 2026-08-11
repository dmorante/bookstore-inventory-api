"""
Esquemas Pydantic para el recurso `Book`.

Se separan explícitamente los esquemas de entrada (create/update) del de
salida (`BookRead`) para que:

- Los campos calculados o generados por el servidor (`id`, `created_at`,
  `selling_price_local`, etc.) no puedan ser enviados por el cliente.
- Las validaciones de negocio (ISBN, cost_usd > 0, stock >= 0) se
  apliquen a nivel de la capa de esquemas y produzcan errores 422
  automáticos con mensajes claros en Swagger.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Validaciones reutilizables
# ---------------------------------------------------------------------------


def _validate_isbn(value: str) -> str:
    """
    Valida y normaliza un ISBN.

    Reglas:
    - Se aceptan guiones y espacios; se eliminan antes de validar.
    - Debe tener exactamente 10 o 13 dígitos.
    - Se retorna el ISBN original (con guiones), no normalizado, para
      preservar la representación humana.
    """
    digits = value.replace("-", "").replace(" ", "")
    if not digits.isdigit():
        raise ValueError("El ISBN solo puede contener dígitos, guiones o espacios.")
    if len(digits) not in (10, 13):
        raise ValueError("El ISBN debe tener 10 o 13 dígitos.")
    return value


def _validate_country(value: str) -> str:
    """Normaliza el código de país a mayúsculas (ISO 3166-1 alpha-2)."""
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("supplier_country debe ser un código ISO alpha-2 (2 letras).")
    return normalized


# ---------------------------------------------------------------------------
# Esquemas base
# ---------------------------------------------------------------------------


class BookBase(BaseModel):
    """Campos comunes a la creación y actualización de un libro."""

    title: Annotated[str, Field(min_length=1, max_length=255, description="Título del libro.", examples=["El Quijote"])]
    author: Annotated[str, Field(min_length=1, max_length=255, description="Autor del libro.", examples=["Miguel de Cervantes"])]
    isbn: Annotated[str, Field(description="ISBN válido de 10 o 13 dígitos. Se aceptan guiones.", examples=["978-84-376-0494-7"])]
    cost_usd: Annotated[float, Field(gt=0, description="Costo del libro en USD. Debe ser mayor a 0.", examples=[15.99])]
    stock_quantity: Annotated[int, Field(ge=0, description="Unidades en stock. No puede ser negativo.", examples=[25])]
    category: Annotated[str, Field(min_length=1, max_length=100, description="Categoría del libro.", examples=["Literatura Clásica"])]
    supplier_country: Annotated[str, Field(description="País del proveedor en formato ISO 3166-1 alpha-2.", examples=["ES"])]

    _validate_isbn = field_validator("isbn")(_validate_isbn)
    _validate_country = field_validator("supplier_country")(_validate_country)


class BookCreate(BookBase):
    """Payload para crear un libro (`POST /books`)."""


class BookUpdate(BaseModel):
    """
    Payload para actualizar un libro (`PUT /books/{id}`).

    Todos los campos son opcionales: solo se actualizan los enviados.
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    isbn: str | None = Field(default=None)
    cost_usd: float | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    supplier_country: str | None = Field(default=None)

    @field_validator("isbn")
    @classmethod
    def _isbn(cls, v: str | None) -> str | None:
        return _validate_isbn(v) if v is not None else None

    @field_validator("supplier_country")
    @classmethod
    def _country(cls, v: str | None) -> str | None:
        return _validate_country(v) if v is not None else None


class BookRead(BookBase):
    """Representación de un libro devuelta por la API."""

    id: int = Field(description="Identificador único del libro.", examples=[1])
    selling_price_local: float | None = Field(
        default=None,
        description="Precio de venta en moneda local. Null hasta que se calcula.",
        examples=[19.03],
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Esquemas para paginación y cálculo de precio
# ---------------------------------------------------------------------------


class PaginatedBooks(BaseModel):
    """Respuesta paginada para `GET /books`."""

    items: list[BookRead]
    total: int = Field(description="Total de libros que cumplen la consulta.")
    skip: int = Field(description="Cantidad de registros omitidos (offset).")
    limit: int = Field(description="Tamaño de la página solicitada.")


class PriceCalculation(BaseModel):
    """Respuesta detallada del cálculo de precio."""

    book_id: int = Field(examples=[1])
    cost_usd: float = Field(examples=[15.99])
    exchange_rate: float = Field(description="Tasa de cambio USD → moneda local aplicada.", examples=[0.85])
    cost_local: float = Field(description="Costo del libro convertido a moneda local.", examples=[13.59])
    margin_percentage: float = Field(description="Margen de ganancia aplicado (%).", examples=[40])
    selling_price_local: float = Field(description="Precio de venta sugerido en moneda local.", examples=[19.03])
    currency: str = Field(description="Código ISO 4217 de la moneda local.", examples=["EUR"])
    calculation_timestamp: datetime = Field(description="Momento (UTC) en que se realizó el cálculo.")
    used_fallback_rate: bool = Field(
        default=False,
        description="Indica si se usó la tasa por defecto porque la API externa falló.",
    )
