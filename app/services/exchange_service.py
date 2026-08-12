"""
Cliente para la API pública de tasas de cambio.

Se aisla en un servicio dedicado para poder:
- Sustituirlo por un mock en tests.
- Cambiar el proveedor externo sin tocar los endpoints.
- Aplicar en un solo lugar el timeout, la caché y la degradación ante
  fallos.
"""

import asyncio
import logging
import time

import httpx

from app.config import Settings
from app.core.exchange_rates import FALLBACK_RATES, RateSource

logger = logging.getLogger(__name__)


class _RateCache:
    """
    Caché en memoria de la última respuesta buena de la API.

    Cumple dos funciones:

    1. **Rendimiento**: evita salir a la red en cada cálculo de precio.
       Mientras la caché esté dentro del TTL, se sirve desde memoria.
    2. **Resiliencia**: si la API deja de responder, las tasas guardadas
       siguen disponibles como respaldo aunque hayan vencido. Una tasa
       real de hace unas horas es mejor aproximación que una constante
       escrita en el código.

    Es un caché de proceso: cada instancia de la aplicación tiene el
    suyo. Suficiente para este caso de uso; con varias réplicas y mucho
    tráfico, el siguiente paso natural sería Redis.
    """

    def __init__(self) -> None:
        self._rates: dict[str, float] = {}
        self._updated_at: float | None = None

    def store(self, rates: dict[str, float]) -> None:
        """Guarda una respuesta completa de la API."""
        self._rates = rates
        self._updated_at = time.monotonic()

    def get(self, currency: str) -> float | None:
        """Devuelve la tasa cacheada de una moneda, sin importar su edad."""
        value = self._rates.get(currency)
        return float(value) if value is not None else None

    def is_fresh(self, ttl_seconds: float) -> bool:
        """Indica si la caché sigue vigente según el TTL configurado."""
        if self._updated_at is None:
            return False
        return (time.monotonic() - self._updated_at) < ttl_seconds


# Caché compartida por todas las instancias del servicio. El servicio se
# construye una vez por request (es una dependencia de FastAPI), así que
# la caché no puede vivir dentro de la instancia.
_cache = _RateCache()

# Evita que varias requests concurrentes disparen la misma consulta HTTP
# cuando la caché acaba de vencer.
_fetch_lock = asyncio.Lock()


class ExchangeRateService:
    """
    Obtiene tasas de cambio USD -> moneda destino.

    La API base devuelve un JSON con la forma::

        {"base": "USD", "date": "...", "rates": {"EUR": 0.92, "MXN": 17.1, ...}}
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_rate(self, currency_code: str) -> tuple[float, RateSource]:
        """
        Devuelve `(tasa, origen)` para la moneda solicitada.

        Resuelve en cascada, de la fuente más precisa a la menos:

        1. Caché vigente o consulta en vivo a la API -> `RateSource.LIVE`.
        2. Última tasa buena conocida, aunque haya vencido, si la API
           falla -> `RateSource.CACHE`.
        3. Tabla de respaldo del código -> `RateSource.DEFAULT`.

        Solo si la moneda no aparece en ninguna de las tres fuentes se
        lanza `RuntimeError`, que la capa superior traduce a un 503.
        """
        currency = currency_code.upper()

        # 1. Caché vigente: evitamos salir a la red.
        if _cache.is_fresh(self._settings.exchange_cache_ttl_seconds):
            cached = _cache.get(currency)
            if cached is not None:
                return cached, RateSource.LIVE

        # 2. Consulta a la API externa.
        await self._refresh_cache()
        if _cache.is_fresh(self._settings.exchange_cache_ttl_seconds):
            fresh = _cache.get(currency)
            if fresh is not None:
                return fresh, RateSource.LIVE

        # 3. La API falló (o no trae esta moneda): última tasa conocida.
        stale = _cache.get(currency)
        if stale is not None:
            logger.warning(
                "Usando tasa cacheada vencida para %s: la API no está disponible.",
                currency,
            )
            return stale, RateSource.CACHE

        # 4. Sin caché: tabla de respaldo.
        if currency in FALLBACK_RATES:
            logger.warning(
                "Usando tasa de respaldo para %s: la API no está disponible "
                "y no hay ninguna tasa cacheada.",
                currency,
            )
            return FALLBACK_RATES[currency], RateSource.DEFAULT

        raise RuntimeError(
            f"No fue posible obtener una tasa para {currency} por ningún medio."
        )

    async def _refresh_cache(self) -> None:
        """
        Consulta la API y actualiza la caché.

        No propaga errores: un fallo de red deja la caché intacta y el
        método `get_rate` continúa con las fuentes de respaldo.
        """
        async with _fetch_lock:
            # Otra request pudo refrescar la caché mientras esperábamos.
            if _cache.is_fresh(self._settings.exchange_cache_ttl_seconds):
                return
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.exchange_api_timeout
                ) as client:
                    response = await client.get(self._settings.exchange_api_url)
                    response.raise_for_status()
                    rates = response.json().get("rates")
                    if rates:
                        _cache.store(rates)
                    else:
                        logger.warning(
                            "La API de tasas respondió sin el campo 'rates'."
                        )
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("Fallo consultando la API de tasas de cambio: %s", exc)
