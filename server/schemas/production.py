from pydantic import BaseModel
from datetime import datetime


class ProductionRecord(BaseModel):
    """
    Schema completo di un record della tabella solar_production.

    Usato per serializzare oggetti SQLAlchemy direttamente grazie a
    model_config from_attributes=True. Non viene esposto direttamente
    nelle risposte API ma può essere usato internamente.
    """
    id: int
    timestamp: datetime
    energy_kwh: float
    radiation_wm2: float | None
    temperature_c: float | None

    model_config = {"from_attributes": True}


class TopEntry(BaseModel):
    """
    Schema per una singola voce nei risultati top-hours e top-radiation.

    Rappresenta un'ora del giorno con la relativa produzione media e irradiazione media.
    Il campo 'ora' mostra l'intervallo orario (es. "12:00 - 13:00").
    """
    ora: str
    avg_energy_kwh: float
    avg_radiation_wm2: float | None = None


class HourlyStats(BaseModel):
    """
    Schema per le statistiche aggregate per ora del giorno (endpoint /averages).

    Riporta per ciascuna ora (0-23) la produzione media e totale
    calcolata su tutti i giorni presenti nel dataset.
    """
    hour: int
    avg_energy_kwh: float
    total_energy_kwh: float


class MonthlyAggregate(BaseModel):
    """
    Schema per l'aggregato mensile di produzione (endpoint /monthly-aggregate).

    Riporta per ogni anno/mese la produzione totale in kWh e
    la media dell'irradiazione solare. Utile per analisi stagionali.
    """
    year: int
    month: int
    total_energy_kwh: float
    avg_radiation_wm2: float | None


class AveragesResponse(BaseModel):
    """
    Schema per la risposta dell'endpoint /averages.

    Raggruppa le statistiche orarie (hourly) e mensili (monthly)
    in un'unica risposta strutturata.
    """
    hourly: list[HourlyStats]
    monthly: list[MonthlyAggregate]


class SuggestionsResponse(BaseModel):
    """
    Schema per la risposta dell'endpoint /suggestions (batch).

    Contiene tutti i risultati in un'unica chiamata:
    top ore per produzione, top ore per irradiazione,
    aggregato mensile e medie orarie/mensili.
    """
    top_hours: list[TopEntry]
    top_radiation: list[TopEntry]
    monthly_aggregate: list[MonthlyAggregate]
    averages: AveragesResponse
