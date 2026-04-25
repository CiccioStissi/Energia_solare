from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.sql import func

from database import Base


class ImportJob(Base):
    """
    Rappresenta un job di importazione CSV nel database.

    Ogni volta che l'admin carica un CSV, viene creato un record ImportJob
    con status='queued'. Il worker aggiorna lo status man mano che elabora.

    Ciclo di vita:
      queued → processing → done
                          → failed (con messaggio di errore in 'error')
    """

    __tablename__ = "import_jobs"

    id = Column(String, primary_key=True)           # UUID generato lato FastAPI
    filename = Column(String, nullable=False)        # nome originale del file CSV
    status = Column(String, nullable=False, default="queued")  # queued|processing|done|failed
    rows_imported = Column(Integer, nullable=True)   # righe processate (valorizzato a done)
    error = Column(Text, nullable=True)              # messaggio di errore (valorizzato a failed)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
