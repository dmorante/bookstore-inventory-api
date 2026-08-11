"""
Cliente para la API pública de tasas de cambio.

Se aisla en un servicio dedicado para poder:
- Sustituirlo por un mock en tests.
- Cambiar el proveedor externo sin tocar los endpoints.
- Aplicar en un solo lugar el timeout y el fallback ante fallos.
"""

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """
    Obtiene tasas de cambio USD → moneda destino.

    La API base devuelve un JSON con la forma::

        {"base": "USD", "date": "...", "rates": {"EUR": 0.92, "MXN": 17.1, ...}}
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_rate(self, currency_code: str) -> tuple[float, bool]:
        """
        Devuelve `(tasa, uso_fallback)` para la moneda solicitada.

        - Si la API responde correctamente y contiene la moneda: retorna
          la tasa real y `False`.
        - Si la API falla (timeout, error de red, HTTP != 200, o la
          moneda no está en la respuesta) y la moneda coincide con la
          `default_fallback_currency`: retorna la tasa de fallback y
          `True`.
        - En cualquier otro caso lanza la excepción original para que
          la capa superior decida (típicamente responderá 503).
        """
        currency = currency_code.upper()
        try:
            async with httpx.AsyncClient(timeout=self._settings.exchange_api_timeout) as client:
                response = await client.get(self._settings.exchange_api_url)
                response.raise_for_status()
                data = response.json()
                rates = data.get("rates") or {}
                if currency in rates:
                    return float(rates[currency]), False
                logger.warning(
                    "La moneda %s no está presente en la respuesta de la API externa.",
                    currency,
                )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Fallo consultando la API de tasas de cambio: %s", exc)

        # Aplicamos fallback solo si coincide con la moneda por defecto.
        if currency == self._settings.default_fallback_currency.upper():
            return self._settings.default_fallback_rate, True

        # Sin fallback disponible para esta moneda: el caller decide qué hacer.
        raise RuntimeError(
            f"No fue posible obtener tasa para {currency} y no hay fallback configurado."
        )
