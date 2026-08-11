"""
Mapeo entre país (ISO 3166-1 alpha-2) y su moneda (ISO 4217).

Se mantiene un subconjunto pragmático de países comunes en la industria
editorial. Si el país no está en el mapa, se levanta
`UnsupportedCurrencyError` para forzar una decisión explícita en vez de
adivinar.
"""

from app.core.exceptions import UnsupportedCurrencyError

COUNTRY_TO_CURRENCY: dict[str, str] = {
    "US": "USD",
    "MX": "MXN",
    "ES": "EUR",
    "FR": "EUR",
    "DE": "EUR",
    "IT": "EUR",
    "PT": "EUR",
    "NL": "EUR",
    "AR": "ARS",
    "CO": "COP",
    "CL": "CLP",
    "PE": "PEN",
    "BR": "BRL",
    "UY": "UYU",
    "GB": "GBP",
    "JP": "JPY",
    "CN": "CNY",
    "CA": "CAD",
    "AU": "AUD",
    "CH": "CHF",
    "IN": "INR",
}


def currency_for_country(country_code: str) -> str:
    """Devuelve el código de moneda ISO 4217 para un país dado."""
    code = country_code.upper()
    if code not in COUNTRY_TO_CURRENCY:
        raise UnsupportedCurrencyError(
            f"No hay moneda mapeada para el país '{code}'."
        )
    return COUNTRY_TO_CURRENCY[code]
