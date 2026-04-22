from sqlalchemy import Column, Integer, Float, DateTime
from database import Base


class SolarProduction(Base):
    """
    Modello SQLAlchemy per la tabella 'solar_production'.

    Rappresenta una singola misurazione oraria del pannello fotovoltaico.
    Il vincolo unique su 'timestamp' garantisce che non esistano due misurazioni
    per lo stesso istante — usato dal csv_importer con ON CONFLICT DO NOTHING
    per rendere le importazioni idempotenti.

    Colonne:
      id             : chiave primaria auto-incrementale
      timestamp      : data e ora della misurazione (unico, indicizzato)
      energy_kwh     : energia prodotta nell'ora in kilowattora (obbligatorio)
      radiation_wm2  : irradiazione solare in W/m² (opzionale, nullable)
      temperature_c  : temperatura in gradi Celsius (opzionale, nullable)
    """

    __tablename__ = "solar_production"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    energy_kwh = Column(Float, nullable=False)
    radiation_wm2 = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
