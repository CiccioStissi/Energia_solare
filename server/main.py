from contextlib import asynccontextmanager
from fastapi import FastAPI
from passlib.context import CryptContext
from sqlalchemy import select

from database import engine, Base, SessionLocal
from models.user import User
from models.production import SolarProduction  # noqa: F401 — registra il modello in Base.metadata
from models.job import ImportJob              # noqa: F401 — registra il modello in Base.metadata
from config import settings
from routers import auth, production, admin
import rabbitmq


# Contesto per l'hashing delle password usato nella creazione dell'admin iniziale
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestisce il ciclo di vita dell'applicazione FastAPI.

    All'avvio:
      - Crea tutte le tabelle nel database (se non esistono già) leggendo
        i modelli registrati in Base.metadata.
      - Verifica se esiste un utente 'admin': se non esiste, lo crea
        con la password definita in FIRST_ADMIN_PASSWORD nel file .env.
    """
    # Crea tutte le tabelle (se non esistono)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Crea utente admin al primo avvio se non esiste
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            hashed = pwd_context.hash(settings.FIRST_ADMIN_PASSWORD)
            db.add(User(username="admin", hashed_password=hashed, role="admin"))
            await db.commit()
            print("✓ Utente admin creato")

    # Connette a RabbitMQ — necessario per pubblicare messaggi da routers/admin.py
    await rabbitmq.connect()
    print("✓ Connessione RabbitMQ stabilita")

    yield

    # Chiude RabbitMQ e il connection pool DB alla chiusura del server
    await rabbitmq.close()
    await engine.dispose()


# Istanza principale dell'applicazione FastAPI
# I metadati (title, description, version) appaiono automaticamente su /docs
app = FastAPI(
    title="Progetto Ingegneria dei sistemi distribuiti - Energia Solare API",
    description="Analisi dati produzione fotovoltaica",
    version="1.0.0",
    lifespan=lifespan,
)

# Registrazione dei router — ogni router gestisce un gruppo di endpoint
app.include_router(auth.router)        # /auth/login, /auth/register
app.include_router(production.router)  # /production/...
app.include_router(admin.router)       # /admin/upload-csv
