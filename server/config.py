from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurazione centralizzata dell'applicazione.

    Legge automaticamente le variabili dal file .env grazie a pydantic-settings.
    Se una variabile obbligatoria manca o ha tipo errato, l'app crasha all'avvio
    con un messaggio chiaro — meglio scoprirlo subito che a runtime.

      DATABASE_URL              : stringa di connessione a PostgreSQL (asyncpg)
      SECRET_KEY                : chiave segreta per firmare i JWT
      ALGORITHM                 : algoritmo di firma JWT (default HS256)
      ACCESS_TOKEN_EXPIRE_MINUTES: durata del token in minuti (default 60)
      FIRST_ADMIN_PASSWORD      : password dell'utente admin creato al primo avvio
    """

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FIRST_ADMIN_PASSWORD: str

    # Indica a pydantic-settings dove trovare il file .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton: unica istanza condivisa da tutti i moduli tramite `from config import settings`
settings = Settings()
