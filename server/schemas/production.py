from pydantic import BaseModel
from datetime import datetime


class ProductionRecord(BaseModel):
    id: int
    timestamp: datetime
    energy_kwh: float
    radiation_wm2: float | None
    temperature_c: float | None

    model_config = {"from_attributes": True}


class TopEntry(BaseModel):
    ora: str
    avg_energy_kwh: float
    avg_radiation_wm2: float | None = None


class HourlyStats(BaseModel):
    hour: int
    avg_energy_kwh: float
    total_energy_kwh: float


class MonthlyAggregate(BaseModel):
    year: int
    month: int
    total_energy_kwh: float
    avg_radiation_wm2: float | None


class AveragesResponse(BaseModel):
    hourly: list[HourlyStats]
    monthly: list[MonthlyAggregate]


class SuggestionsResponse(BaseModel):
    top_hours: list[TopEntry]
    top_radiation: list[TopEntry]
    monthly_aggregate: list[MonthlyAggregate]
    averages: AveragesResponse
