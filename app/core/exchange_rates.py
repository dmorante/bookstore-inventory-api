"""
Tasas de respaldo y trazabilidad del origen de una tasa de cambio.

El enunciado exige que, si la API de tasas falla, el cálculo de precio
siga funcionando con una tasa por defecto. Para cumplirlo sin devolver
números arbitrarios, la resolución de una tasa sigue este orden:

1. **Tasa en vivo** de la API externa.
2. **Última tasa buena conocida**, guardada en caché. Es una tasa real
   obtenida de la API, solo que no en este mismo instante.
3. **Tabla de respaldo** de este módulo, para cuando la API falla y aún
   no se ha podido cachear nada (por ejemplo, si falla en el primer
   arranque del servicio).

`RateSource` permite saber cuál de los tres caminos se usó, información
que se expone en la respuesta del endpoint de cálculo de precio.
"""

from enum import Enum


class RateSource(str, Enum):
    """Origen de la tasa de cambio empleada en un cálculo."""

    LIVE = "live"
    """Consultada a la API externa (directamente o dentro del TTL de caché)."""

    CACHE = "cache"
    """La API falló; se reutilizó la última tasa real conocida."""

    DEFAULT = "default"
    """La API falló y no había caché; se usó la tabla de respaldo."""


# Tasas USD -> moneda local usadas como último recurso.
#
# Son valores aproximados, capturados de la propia API en 2026-08-11, y
# existen solo para que el servicio degrade con elegancia en lugar de
# fallar. Una tasa de esta tabla es, por definición, imprecisa: la
# respuesta del endpoint lo indica con `rate_source: "default"` y
# `used_fallback_rate: true` para que el consumidor no la confunda con
# una cotización vigente.
#
# Cubre todas las monedas de `COUNTRY_TO_CURRENCY`; al añadir un país
# nuevo allí conviene añadir aquí su moneda.
FALLBACK_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.866,
    "MXN": 17.1,
    "ARS": 1492.18,
    "COP": 3136.62,
    "CLP": 915.92,
    "PEN": 3.37,
    "BRL": 5.12,
    "UYU": 40.27,
    "GBP": 0.74,
    "JPY": 159.29,
    "CNY": 6.76,
    "CAD": 1.39,
    "AUD": 1.42,
    "CHF": 0.811,
    "INR": 95.46,
}
