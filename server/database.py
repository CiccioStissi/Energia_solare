from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from config import settings


engine = create_async_engine(settings.DATABASE_URL, echo=False)

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
