"""
Punto de entrada de la aplicación FastAPI.

Aquí se:
- Instancia la app y se configuran metadatos que aparecen en Swagger.
- Registran los routers.
- Registran los handlers globales de excepciones de dominio.
- Expone un endpoint `/health` para health checks del despliegue.
- Se sirve ReDoc con una versión fija de su bundle (ver más abajo).
"""

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html

from app.config import get_settings
from app.core.exceptions import DomainError, domain_error_handler
from app.routers import books

settings = get_settings()

# Versión fija del bundle de ReDoc.
#
# Por defecto FastAPI apunta a `redoc@next`, un tag de pre-release que
# dejó de publicarse en jsDelivr y hoy responde 404: la página de /redoc
# carga pero queda en blanco porque nunca llega el JavaScript. Fijamos una
# versión concreta (en vez de un tag móvil como `@next` o `@2`) para que
# la documentación no vuelva a romperse por un cambio en el CDN.
REDOC_JS_URL = "https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js"

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
    # Desactivamos la ruta automática de ReDoc para servirla nosotros más
    # abajo con una versión fija del bundle. Swagger UI (/docs) se mantiene
    # con la configuración por defecto.
    redoc_url=None,
)

# Handlers globales para excepciones de dominio -> respuestas HTTP consistentes.
app.add_exception_handler(DomainError, domain_error_handler)

# Routers de recursos.
app.include_router(books.router)


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Sirve ReDoc apuntando a una versión fija de su bundle."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url=REDOC_JS_URL,
    )


@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Devuelve `{'status': 'ok'}` si el servicio está operativo.",
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
