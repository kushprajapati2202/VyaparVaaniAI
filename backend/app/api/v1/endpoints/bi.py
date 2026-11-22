from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.schemas import DailySummaryResponse
from app.services.bi_service import BIService

router = APIRouter()

@router.get("/daily-summary", response_model=DailySummaryResponse)
async def get_daily_summary(db: AsyncSession = Depends(get_db)):
    metrics = await BIService.get_daily_metrics(db)
    return DailySummaryResponse(**metrics)


@router.get("/impact")
async def get_impact(db: AsyncSession = Depends(get_db)):
    """ROI / unit economics measured from voice-agent activity."""
    return await BIService.get_impact_metrics(db)
