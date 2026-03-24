"""
System statistics routes for tracking total users and debug logins
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import SystemStats, User

router = APIRouter(prefix="/stats", tags=["system statistics"])

class StatsResponse(BaseModel):
    total_users: int
    debug_logins: int

class StatsIncrementRequest(BaseModel):
    increment_debug: bool = False
    increment_total_users: bool = False

@router.get("/", response_model=StatsResponse)
async def get_system_stats(db: Session = Depends(get_db)):
    """
    Get current system statistics
    """
    stats = db.query(SystemStats).first()
    
    if not stats:
        # Initialize stats if not exists
        stats = SystemStats(
            total_users=db.query(User).count(),
            debug_logins=0
        )
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
    return StatsResponse(
        total_users=stats.total_users,
        debug_logins=stats.debug_logins
    )

@router.post("/increment", response_model=StatsResponse)
async def increment_stats(
    request: StatsIncrementRequest,
    db: Session = Depends(get_db)
):
    """
    Increment system statistics
    - increment_debug: True to increment debug login count
    - increment_total_users: True to increment total users count
    """
    stats = db.query(SystemStats).first()
    
    if not stats:
        # Initialize stats if not exists
        stats = SystemStats(
            total_users=1 if request.increment_total_users else db.query(User).count(),
            debug_logins=1 if request.increment_debug else 0
        )
        db.add(stats)
    else:
        if request.increment_debug:
            stats.debug_logins += 1
        
        if request.increment_total_users:
            stats.total_users += 1
        else:
            # Update total users count from actual user count if not specifically incrementing
            stats.total_users = db.query(User).count()
    
    db.commit()
    db.refresh(stats)
    
    return StatsResponse(
        total_users=stats.total_users,
        debug_logins=stats.debug_logins
    )
