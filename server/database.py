from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from config import settings


# Engine asincrono: gestisce il connection pool verso PostgreSQL.
# echo=False disabilita il logging SQL in console (impostare True per debug).
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Factory per creare sessioni asincrone.
# expire_on_commit=False evita che gli oggetti vengano "scaduti" dopo il commit,
# permettendo di accedere ai loro attributi senza riaprire la sessione.
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Classe base per tutti i modelli SQLAlchemy.

    Ogni modello che eredita da Base viene automaticamente registrato
    in Base.metadata, che viene usato da main.py per creare le tabelle
    con create_all al primo avvio.
    """
    pass


async def get_db():
    """
    Dependency injection per FastAPI: fornisce una sessione database agli endpoint.

    Flusso:
      Richiesta HTTP → FastAPI chiama get_db → apre sessione → endpoint esegue query
      → risposta inviata → sessione chiusa automaticamente
    """
    async with SessionLocal() as session:
        yield session
