"""
Configuración de la aplicación.

Se centraliza en un único objeto `Settings` (patrón Singleton vía
`lru_cache`) que lee variables de entorno o el archivo `.env`.
Esto permite:

- Cambiar comportamiento entre entornos (local, Docker, producción) sin
  tocar código.
- Inyectar la configuración por dependencia en los endpoints (útil para
  pruebas).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno tipadas y validadas por Pydantic."""

    # Metadatos de la app (se muestran en Swagger)
    app_name: str = Field(default="Bookstore Inventory API")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)

    # Base de datos. Debe ser una URL SQLAlchemy async
    # (p. ej. postgresql+asyncpg://user:pass@host:5432/db).
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/bookstore",
    )

    # API externa de tasas de cambio.
    exchange_api_url: str = Field(
        default="https://api.exchangerate-api.com/v4/latest/USD",
    )
    exchange_api_timeout: float = Field(default=5.0)

    # Reglas de negocio.
    default_margin_percentage: float = Field(default=40.0)
    default_fallback_rate: float = Field(default=0.92)
    default_fallback_currency: str = Field(default="EUR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia global de Settings (cacheada)."""
    return Settings()
