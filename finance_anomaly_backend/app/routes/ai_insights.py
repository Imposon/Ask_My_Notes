from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ai_insight_service import generate_financial_insights

router = APIRouter(prefix="/ai-insights", tags=["AI Insights"])

@router.post("/{user_id}")
def get_insights(user_id: str, db: Session = Depends(get_db)):
    """
    Generate proactive AI financial insights utilizing OpenAI's GPT models.
    """
    result = generate_financial_insights(db=db, user_id=user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
