"""
Endpoints REST del recurso `Book`.

Todas las respuestas y errores están documentados con `responses=...`
para que Swagger UI muestre ejemplos completos.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_book_service
from app.schemas.book import (
    BookCreate,
    BookRead,
    BookUpdate,
    PaginatedBooks,
    PriceCalculation,
)
from app.services.book_service import BookService

router = APIRouter(prefix="/books", tags=["books"])


# ---------------------------------------------------------------------------
# Endpoints opcionales primero (rutas específicas antes que /{book_id})
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    response_model=list[BookRead],
    summary="Buscar libros por categoría",
    description=(
        "Devuelve todos los libros que coincidan exactamente con la categoría "
        "indicada. La búsqueda es case-sensitive."
    ),
)
async def search_books(
    category: Annotated[str, Query(min_length=1, description="Categoría exacta a buscar.", examples=["Literatura Clásica"])],
    service: Annotated[BookService, Depends(get_book_service)],
) -> list[BookRead]:
    items, _ = await service.list_all(skip=0, limit=1000, category=category)
    return [BookRead.model_validate(b) for b in items]


@router.get(
    "/low-stock",
    response_model=list[BookRead],
    summary="Listar libros con stock bajo",
    description=(
        "Retorna los libros cuyo `stock_quantity` sea menor o igual al umbral "
        "indicado. Útil para alertas de reabastecimiento."
    ),
)
async def low_stock_books(
    service: Annotated[BookService, Depends(get_book_service)],
    threshold: Annotated[int, Query(ge=0, description="Umbral máximo de stock.", examples=[10])] = 10,
) -> list[BookRead]:
    items = await service.low_stock(threshold)
    return [BookRead.model_validate(b) for b in items]


# ---------------------------------------------------------------------------
# CRUD principal
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo libro",
    description=(
        "Crea un libro en el inventario. Valida ISBN, cost_usd > 0 y "
        "stock >= 0. Falla con **400** si el ISBN ya existe."
    ),
    responses={
        400: {"description": "ISBN duplicado o datos inválidos."},
        422: {"description": "Error de validación de esquema."},
    },
)
async def create_book(
    payload: BookCreate,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    book = await service.create(payload)
    return BookRead.model_validate(book)


@router.get(
    "",
    response_model=PaginatedBooks,
    summary="Listar libros",
    description="Devuelve todos los libros con paginación por `skip`/`limit`.",
)
async def list_books(
    service: Annotated[BookService, Depends(get_book_service)],
    skip: Annotated[int, Query(ge=0, description="Registros a omitir (offset).")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Tamaño de página (1-100).")] = 20,
) -> PaginatedBooks:
    items, total = await service.list_all(skip=skip, limit=limit)
    return PaginatedBooks(
        items=[BookRead.model_validate(b) for b in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{book_id}",
    response_model=BookRead,
    summary="Obtener libro por ID",
    responses={404: {"description": "Libro no encontrado."}},
)
async def get_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    book = await service.get(book_id)
    return BookRead.model_validate(book)


@router.put(
    "/{book_id}",
    response_model=BookRead,
    summary="Actualizar libro",
    description="Actualiza uno o más campos de un libro existente.",
    responses={
        400: {"description": "ISBN duplicado."},
        404: {"description": "Libro no encontrado."},
        422: {"description": "Error de validación de esquema."},
    },
)
async def update_book(
    book_id: int,
    payload: BookUpdate,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookRead:
    book = await service.update(book_id, payload)
    return BookRead.model_validate(book)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar libro",
    responses={404: {"description": "Libro no encontrado."}},
)
async def delete_book(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> None:
    await service.delete(book_id)


# ---------------------------------------------------------------------------
# Cálculo de precio (integración externa)
# ---------------------------------------------------------------------------


@router.post(
    "/{book_id}/calculate-price",
    response_model=PriceCalculation,
    summary="Calcular precio de venta sugerido",
    description=(
        "Calcula el precio de venta en moneda local aplicando la tasa de "
        "cambio USD → moneda del país del proveedor más un margen "
        "configurable (por defecto 40%). "
        "Actualiza `selling_price_local` del libro y retorna el desglose.\n\n"
        "- **400**: país del proveedor sin moneda soportada.\n"
        "- **404**: libro no encontrado.\n"
        "- **503**: API externa caída y sin fallback aplicable."
    ),
    responses={
        400: {"description": "Moneda no soportada para el país del proveedor."},
        404: {"description": "Libro no encontrado."},
        503: {"description": "Servicio de tasas de cambio no disponible."},
    },
)
async def calculate_price(
    book_id: int,
    service: Annotated[BookService, Depends(get_book_service)],
) -> PriceCalculation:
    return await service.calculate_price(book_id)
