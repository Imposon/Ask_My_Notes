import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import create_all, get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.routes.upload import router as upload_router
from app.routes.analyze import router as analyze_router
from app.routes.ai_insights import router as ai_insights_router
from app.utils.helpers import ensure_ml_models_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    ensure_ml_models_dir()
    yield


app = FastAPI(
    title="Personal Finance Anomaly Detector",
    description="AI-powered anomaly detection for bank transactions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(ai_insights_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/users", response_model=UserResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        return existing
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
