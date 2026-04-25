from sqlalchemy import Column, Integer, Float, DateTime
from database import Base


class SolarProduction(Base):
    __tablename__ = "solar_production"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    energy_kwh = Column(Float, nullable=False)
    radiation_wm2 = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
