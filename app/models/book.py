"""
Modelo SQLModel `Book` — representación de un libro en el inventario.

En SQLModel un mismo tipo puede ser a la vez modelo de tabla y esquema
Pydantic. Aquí seguimos el patrón recomendado por la documentación:

- `BookBase`: campos comunes y validaciones. NO es una tabla.
  Sirve como base para la tabla y para los esquemas de la API.
- `Book`: hereda de `BookBase` con `table=True`, añade el `id` primario,
  el ISBN único, `selling_price_local` y timestamps.

Reutilizar `BookBase` evita duplicar la definición de los campos entre
el modelo ORM y los esquemas de request/response.
"""

from datetime import datetime
from typing import Optional

from pydantic import field_validator
from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Validaciones reutilizables
# ---------------------------------------------------------------------------


def validate_isbn(value: str) -> str:
    """
    Valida un ISBN.

    Reglas:
    - Se aceptan guiones y espacios; se ignoran al contar dígitos.
    - Debe tener exactamente 10 o 13 dígitos.
    - Se retorna el ISBN original (con guiones) para preservar la
      representación humana.
    """
    digits = value.replace("-", "").replace(" ", "")
    if not digits.isdigit():
        raise ValueError("El ISBN solo puede contener dígitos, guiones o espacios.")
    if len(digits) not in (10, 13):
        raise ValueError("El ISBN debe tener 10 o 13 dígitos.")
    return value


def validate_country(value: str) -> str:
    """Normaliza el código de país a mayúsculas (ISO 3166-1 alpha-2)."""
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError("supplier_country debe ser un código ISO alpha-2 (2 letras).")
    return normalized


# ---------------------------------------------------------------------------
# SQLModel base y tabla
# ---------------------------------------------------------------------------


class BookBase(SQLModel):
    """
    Campos y validaciones comunes al recurso Book.

    Al no llevar `table=True`, esta clase NO crea una tabla en la BD:
    se usa como base compartida entre `Book` (la tabla) y los esquemas
    `BookCreate` / `BookRead`.
    """

    title: str = Field(min_length=1, max_length=255, description="Título del libro.")
    author: str = Field(min_length=1, max_length=255, description="Autor del libro.")
    isbn: str = Field(max_length=20, description="ISBN válido de 10 o 13 dígitos. Se aceptan guiones.")
    cost_usd: float = Field(gt=0, description="Costo del libro en USD. Debe ser mayor a 0.")
    stock_quantity: int = Field(default=0, ge=0, description="Unidades en stock. No puede ser negativo.")
    category: str = Field(min_length=1, max_length=100, description="Categoría del libro.")
    supplier_country: str = Field(default="US", min_length=2, max_length=2, description="País del proveedor en formato ISO alpha-2 (Por Defecto USD).")

    @field_validator("isbn")
    @classmethod
    def _v_isbn(cls, v: str) -> str:
        return validate_isbn(v)

    @field_validator("supplier_country")
    @classmethod
    def _v_country(cls, v: str) -> str:
        return validate_country(v)


class Book(BookBase, table=True):
    """
    Libro dentro del inventario (tabla `books`).

    Redefine `isbn` para añadirle `unique=True` e `index=True` a nivel
    de columna. Añade el ID primario, el precio local calculado y los
    timestamps gestionados por la BD.
    """

    __tablename__ = "books"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Redefinición para agregar constraints a nivel de tabla.
    isbn: str = Field(max_length=20, unique=True, index=True)

    # Categoría indexada para acelerar `GET /books/search?category=...`.
    category: str = Field(min_length=1, max_length=100, index=True)

    # Precio de venta en moneda local. Null hasta que se calcula.
    selling_price_local: Optional[float] = Field(default=None)

    # Timestamps: usamos sa_column para delegar el default al servidor
    # de BD y garantizar consistencia aunque se hagan inserts fuera de
    # la app (p. ej. desde una migración de datos).
    created_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )
