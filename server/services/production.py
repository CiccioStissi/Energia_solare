from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from models.production import SolarProduction


class ProductionService:
    """
    Service layer per le analisi sui dati di produzione solare.

    Contiene tutta la logica di business e le query SQL aggregate.
    I router delegano a questi metodi statici senza contenere logica propria.
    """

    @staticmethod
    async def top_hours(db: AsyncSession, limit: int = 10) -> list[dict]:
        """
        Restituisce le ore del giorno con la più alta produzione energetica media.

        Raggruppa tutti i record per ora del giorno (extract hour) e calcola
        la media e il totale di energy_kwh per ciascuna ora.
        Ordina per media decrescente e limita ai primi 'limit' risultati.

        Esempio con limit=3: potrebbe restituire ore 12, 13, 11 come
        le tre fasce orarie più produttive in media su tutto il dataset.

        Args:
          db: sessione database asincrona.
          limit: numero massimo di ore da restituire (default 10).

        Returns:
          Lista di dizionari con 'ora' (intervallo es. "12:00 - 13:00"),
          'avg_energy_kwh' e 'total_energy_kwh'.
        """
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
        """
        Restituisce le ore del giorno con la più alta irradiazione solare media.

        Esclude i record con radiation_wm2 nullo, raggruppa per ora del giorno
        e ordina per media irradiazione decrescente.
        Include anche la media di energy_kwh per confronto.

        Args:
          db: sessione database asincrona.
          limit: numero massimo di ore da restituire (default 10).

        Returns:
          Lista di dizionari con 'ora', 'avg_radiation_wm2' e 'avg_energy_kwh'.
        """
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
        """
        Restituisce la produzione totale e l'irradiazione media per ogni mese.

        Raggruppa i dati per anno e mese usando extract(), calcola la somma
        dell'energia prodotta e la media dell'irradiazione per ogni periodo.
        I risultati sono ordinati cronologicamente.

        Args:
          db: sessione database asincrona.

        Returns:
          Lista di dizionari con 'year', 'month', 'total_energy_kwh', 'avg_radiation_wm2'.
        """
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
        """
        Restituisce le medie di produzione per ora del giorno e per mese.

        Combina due query:
          - hourly: per ogni ora del giorno (0-23) calcola media e totale energia,
            ordinato per ora crescente (utile per vedere il profilo giornaliero)
          - monthly: delega a monthly_aggregate per l'andamento mensile

        Args:
          db: sessione database asincrona.

        Returns:
          Dizionario con chiavi 'hourly' (lista HourlyStats) e 'monthly' (lista MonthlyAggregate).
        """
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
        """
        Endpoint batch: aggrega tutti i risultati in un'unica risposta.

        Chiama internamente top_hours, top_radiation, monthly_aggregate e averages
        e li restituisce in un unico dizionario. Permette al client di ottenere
        tutte le analisi con una sola richiesta HTTP invece di quattro.

        Args:
          db: sessione database asincrona.

        Returns:
          Dizionario con chiavi 'top_hours', 'top_radiation', 'monthly_aggregate', 'averages'.
        """
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
