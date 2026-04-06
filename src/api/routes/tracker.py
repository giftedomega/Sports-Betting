"""Bet tracker API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from src.database.persistence import DatabasePersistence
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class BetCreate(BaseModel):
    fixture_id: Optional[int] = None
    match_description: str
    market: str
    selection: str
    odds: float
    stake: float
    notes: Optional[str] = None


class BetUpdate(BaseModel):
    result: Optional[str] = None  # won, lost, void, pending
    odds: Optional[float] = None
    stake: Optional[float] = None
    notes: Optional[str] = None


@router.get("/bets")
async def get_bets(limit: int = 100):
    """Get all tracked bets."""
    try:
        db = DatabasePersistence()
        bets = db.get_tracked_bets(limit=limit)
        return {"bets": bets, "count": len(bets)}
    except Exception as e:
        logger.error(f"Failed to get bets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bets")
async def create_bet(bet: BetCreate):
    """Track a new bet."""
    try:
        db = DatabasePersistence()
        bet_id = db.save_tracked_bet(bet.model_dump())
        if bet_id:
            return {"id": bet_id, "message": "Bet tracked successfully"}
        raise HTTPException(status_code=500, detail="Failed to save bet")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bets/{bet_id}")
async def update_bet(bet_id: int, updates: BetUpdate):
    """Update a tracked bet (e.g., set result)."""
    try:
        db = DatabasePersistence()
        success = db.update_tracked_bet(bet_id, updates.model_dump(exclude_none=True))
        if success:
            return {"message": "Bet updated", "id": bet_id}
        raise HTTPException(status_code=404, detail="Bet not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bets/{bet_id}")
async def delete_bet(bet_id: int):
    """Delete a tracked bet."""
    try:
        db = DatabasePersistence()
        success = db.delete_tracked_bet(bet_id)
        if success:
            return {"message": "Bet deleted", "id": bet_id}
        raise HTTPException(status_code=404, detail="Bet not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_betting_summary():
    """Get betting P&L summary."""
    try:
        db = DatabasePersistence()
        return db.get_betting_summary()
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
