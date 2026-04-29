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
    return await ProductionService.top_hours(db, limit)


@router.get("/top-radiation")
async def top_radiation(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ProductionService.top_radiation(db, limit)


@router.get("/monthly-aggregate")
async def monthly_aggregate(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ProductionService.monthly_aggregate(db)


@router.get("/averages")
async def averages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ProductionService.averages(db)


@router.get("/suggestions")
async def suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ProductionService.suggestions(db)
