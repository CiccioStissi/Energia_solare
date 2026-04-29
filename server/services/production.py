from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from models.production import SolarProduction


class ProductionService:
    """
    Service layer per le analisi sui dati di produzione solare.
    I router delegano a questi metodi statici senza contenere logica propria.
    """

    @staticmethod
    async def top_hours(db: AsyncSession, limit: int = 10) -> list[dict]:
        result = await db.execute(
            select(
                extract("hour", SolarProduction.timestamp).label("ora"),
                func.avg(SolarProduction.energy_kwh).label("avg_energy_kwh"),
                func.sum(SolarProduction.energy_kwh).label("total_energy_kwh"),
            )
            .group_by(extract("hour", SolarProduction.timestamp))
            .order_by(func.avg(SolarProduction.energy_kwh).desc())
            .limit(limit)
        )
        return [
            {
                "ora": f"{int(row.ora):02d}:00 - {int(row.ora)+1:02d}:00",
                "avg_energy_kwh": round(row.avg_energy_kwh, 4),
                "total_energy_kwh": round(row.total_energy_kwh, 3),
            }
            for row in result.all()
        ]

    @staticmethod
    async def top_radiation(db: AsyncSession, limit: int = 10) -> list[dict]:
        result = await db.execute(
            select(
                extract("hour", SolarProduction.timestamp).label("ora"),
                func.avg(SolarProduction.radiation_wm2).label("avg_radiation_wm2"),
                func.avg(SolarProduction.energy_kwh).label("avg_energy_kwh"),
            )
            .where(SolarProduction.radiation_wm2.isnot(None))
            .group_by(extract("hour", SolarProduction.timestamp))
            .order_by(func.avg(SolarProduction.radiation_wm2).desc())
            .limit(limit)
        )
        return [
            {
                "ora": f"{int(row.ora):02d}:00 - {int(row.ora)+1:02d}:00",
                "avg_radiation_wm2": round(row.avg_radiation_wm2, 2),
                "avg_energy_kwh": round(row.avg_energy_kwh, 4),
            }
            for row in result.all()
        ]

    @staticmethod
    async def monthly_aggregate(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                extract("year", SolarProduction.timestamp).label("year"),
                extract("month", SolarProduction.timestamp).label("month"),
                func.sum(SolarProduction.energy_kwh).label("total_energy_kwh"),
                func.avg(SolarProduction.radiation_wm2).label("avg_radiation_wm2"),
            )
            .group_by(
                extract("year", SolarProduction.timestamp),
                extract("month", SolarProduction.timestamp),
            )
            .order_by(
                extract("year", SolarProduction.timestamp),
                extract("month", SolarProduction.timestamp),
            )
        )
        return [
            {
                "year": int(row.year),
                "month": int(row.month),
                "total_energy_kwh": round(row.total_energy_kwh, 3),
                "avg_radiation_wm2": round(row.avg_radiation_wm2, 2) if row.avg_radiation_wm2 else None,
            }
            for row in result.all()
        ]

    @staticmethod
    async def averages(db: AsyncSession) -> dict:
        hourly_result = await db.execute(
            select(
                extract("hour", SolarProduction.timestamp).label("hour"),
                func.avg(SolarProduction.energy_kwh).label("avg_energy_kwh"),
                func.sum(SolarProduction.energy_kwh).label("total_energy_kwh"),
            )
            .group_by(extract("hour", SolarProduction.timestamp))
            .order_by(extract("hour", SolarProduction.timestamp))
        )
        hourly = [
            {
                "hour": int(row.hour),
                "avg_energy_kwh": round(row.avg_energy_kwh, 4),
                "total_energy_kwh": round(row.total_energy_kwh, 3),
            }
            for row in hourly_result.all()
        ]

        monthly = await ProductionService.monthly_aggregate(db)

        return {"hourly": hourly, "monthly": monthly}

    @staticmethod
    async def suggestions(db: AsyncSession) -> dict:
        top_h = await ProductionService.top_hours(db, 5)
        top_r = await ProductionService.top_radiation(db, 5)
        monthly = await ProductionService.monthly_aggregate(db)
        avgs = await ProductionService.averages(db)

        return {
            "top_hours": top_h,
            "top_radiation": top_r,
            "monthly_aggregate": monthly,
            "averages": avgs,
        }
