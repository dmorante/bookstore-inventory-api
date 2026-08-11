"""
Excepciones de dominio y su mapeo a respuestas HTTP.

Al centralizar los errores aquí se logra:
- Respuestas HTTP consistentes en toda la API (mismo formato JSON).
- Separar el "qué salió mal" (dominio) del "cómo se comunica al cliente"
  (HTTP), evitando `HTTPException` esparcidos por los servicios.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Error base del dominio. No debería usarse directamente."""

    status_code: int = 500
    default_detail: str = "Error interno"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.default_detail)
        self.detail = detail or self.default_detail


class BookNotFoundError(DomainError):
    """El libro solicitado no existe."""

    status_code = 404
    default_detail = "Libro no encontrado"


class DuplicateISBNError(DomainError):
    """Ya existe un libro con el mismo ISBN."""

    status_code = 400
    default_detail = "Ya existe un libro con ese ISBN"


class ExchangeRateUnavailableError(DomainError):
    """
    La API externa de tasas de cambio no está disponible.

    Se usa cuando ni la API externa ni el fallback pueden entregar una
    tasa. Se traduce a 503 Service Unavailable.
    """

    status_code = 503
    default_detail = "Servicio de tasas de cambio no disponible"


class UnsupportedCurrencyError(DomainError):
    """No hay tasa disponible para la moneda solicitada."""

    status_code = 400
    default_detail = "Moneda no soportada para el país del proveedor"


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Handler global que convierte cualquier `DomainError` a JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
