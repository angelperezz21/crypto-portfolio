"""
Configuración centralizada de la aplicación.
Lee todas las variables de entorno usando pydantic-settings.
NUNCA hardcodear valores sensibles aquí.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Base de datos -------------------------------------------------------
    # URL asíncrona (asyncpg) para el servidor FastAPI
    DATABASE_URL: str

    # URL síncrona (psycopg2) usada exclusivamente por Alembic para migraciones
    DATABASE_SYNC_URL: str

    # --- Redis ---------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Seguridad -----------------------------------------------------------
    # Clave para firmar tokens JWT. Genera con: secrets.token_hex(32)
    SECRET_KEY: str

    # Clave AES-256-GCM (32 bytes en base64 url-safe) para cifrar API Keys de Binance en BD.
    # Genera con: base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    ENCRYPTION_KEY: str

    # Contraseña de acceso a la aplicación web (sistema personal, un usuario)
    APP_PASSWORD: str

    # Tiempo de vida del token JWT en minutos
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Timeout de sesión en minutos
    SESSION_TIMEOUT_MINUTES: int = 60

    # --- Aplicación ----------------------------------------------------------
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"

    # Orígenes CORS permitidos (cadena separada por comas)
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Sincronización con Binance ------------------------------------------
    # Intervalo mínimo: 5 minutos (RF-02.1)
    SYNC_INTERVAL_MINUTES: int = 5

    # URL base de la API de Binance (permite apuntar a testnet en desarrollo)
    BINANCE_API_BASE_URL: str = "https://api.binance.com"

    # --- Backups -------------------------------------------------------------
    BACKUP_DIR: str = "/backups"

    # --- Propiedades calculadas ----------------------------------------------
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("SYNC_INTERVAL_MINUTES")
    @classmethod
    def validate_sync_interval(cls, v: int) -> int:
        if v < 5:
            raise ValueError("SYNC_INTERVAL_MINUTES debe ser >= 5 (límite de la API de Binance)")
        return v

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        allowed = {"development", "production", "test"}
        if v not in allowed:
            raise ValueError(f"APP_ENV debe ser uno de: {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL debe ser uno de: {allowed}")
        return v.upper()


@lru_cache
def get_settings() -> Settings:
    """Instancia singleton de Settings, cacheada para evitar re-lecturas del .env."""
    return Settings()


# Exportación conveniente para importar directamente en otros módulos
settings: Settings = get_settings()
