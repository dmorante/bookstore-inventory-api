"""
Punto de entrada de la aplicación FastAPI.

Aquí se:
- Instancia la app y se configuran metadatos que aparecen en Swagger.
- Registran los routers.
- Registran los handlers globales de excepciones de dominio.
- Expone un endpoint `/health` para health checks del despliegue.
"""

from fastapi import FastAPI

from app.config import get_settings
from app.core.exceptions import DomainError, domain_error_handler
from app.routers import books

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "API REST para la gestión del inventario de una cadena de librerías.\n\n"
        "Permite operaciones CRUD sobre libros, búsqueda por categoría, "
        "consulta de stock bajo y cálculo del precio de venta sugerido "
        "usando tasas de cambio en tiempo real.\n\n"
        "**Reglas de negocio principales:**\n"
        "- `cost_usd` debe ser mayor a 0.\n"
        "- `stock_quantity` no puede ser negativo.\n"
        "- `isbn` debe tener 10 o 13 dígitos y ser único.\n"
        "- Al calcular precio, si la API de tasas falla se usa una tasa por "
        "defecto configurable."
    ),
    contact={
        "name": "Bookstore Inventory API",
    },
    openapi_tags=[
        {
            "name": "books",
            "description": "Operaciones sobre el inventario de libros.",
        },
        {
            "name": "health",
            "description": "Verificación del estado del servicio.",
        },
    ],
)

# Handlers globales para excepciones de dominio -> respuestas HTTP consistentes.
app.add_exception_handler(DomainError, domain_error_handler)

# Routers de recursos.
app.include_router(books.router)


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Devuelve `{'status': 'ok'}` si el servicio está operativo.",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
