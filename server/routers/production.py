from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth.dependencies import get_current_user
from models.user import User
from services.production import ProductionService


router = APIRouter(prefix="/production", tags=["production"])


@router.get("/top-hours")
async def top_hours(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Restituisce le ore del giorno con la più alta produzione energetica media.

    Raggruppa i dati per ora del giorno (0-23) e ordina per media energia decrescente.
    Con limit=5 restituisce le 5 ore migliori (es. 11:00-12:00, 12:00-13:00, ecc.).
    Accessibile a tutti gli utenti autenticati (user e admin).

    Args:
      limit: numero di ore da restituire (1-100, default 10).
      db: sessione database.
      current_user: utente autenticato (verifica JWT).
    """
    return await ProductionService.top_hours(db, limit)


@router.get("/top-radiation")
async def top_radiation(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Restituisce le ore del giorno con la più alta irradiazione solare media.

    Raggruppa per ora del giorno escludendo i record senza radiation_wm2,
    e ordina per media irradiazione decrescente.
    Accessibile a tutti gli utenti autenticati (user e admin).

    Args:
      limit: numero di ore da restituire (1-100, default 10).
      db: sessione database.
      current_user: utente autenticato (verifica JWT).
    """
    return await ProductionService.top_radiation(db, limit)


@router.get("/monthly-aggregate")
async def monthly_aggregate(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Restituisce la produzione totale e l'irradiazione media aggregata per mese.

    Raggruppa i dati per anno e mese, utile per analisi stagionali e
    confronto tra periodi dell'anno.
    Accessibile a tutti gli utenti autenticati (user e admin).

    Args:
      db: sessione database.
      current_user: utente autenticato (verifica JWT).
    """
    return await ProductionService.monthly_aggregate(db)


@router.get("/averages")
async def averages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Restituisce le medie di produzione per ora del giorno e per mese.

    Combina due aggregazioni:
      - hourly: media e totale per ora del giorno (0-23)
      - monthly: totale e media irradiazione per anno/mese

    Accessibile a tutti gli utenti autenticati (user e admin).

    Args:
      db: sessione database.
      current_user: utente autenticato (verifica JWT).
    """
    return await ProductionService.averages(db)


@router.get("/suggestions")
async def suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint batch: restituisce tutte le analisi in un'unica chiamata.

    Aggrega i risultati di top_hours, top_radiation, monthly_aggregate e averages
    in un singolo oggetto JSON. Permette al client di fare una sola richiesta HTTP
    invece di quattro separate.
    Accessibile a tutti gli utenti autenticati (user e admin).

    Args:
      db: sessione database.
      current_user: utente autenticato (verifica JWT).
    """
    return await ProductionService.suggestions(db)
