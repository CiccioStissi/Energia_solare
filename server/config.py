from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurazione centralizzata dell'applicazione.

    Legge automaticamente le variabili dal file .env grazie a pydantic-settings.
    """

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FIRST_ADMIN_PASSWORD: str
    RABBITMQ_URL: str = "amqp://guest:guest@localhost/"

    # Indica a pydantic-settings dove trovare il file .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton: unica istanza condivisa da tutti i moduli tramite `from config import settings`
settings = Settings()
