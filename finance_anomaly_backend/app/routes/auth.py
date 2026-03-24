"""
Authentication routes for Google OAuth
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

class GoogleAuthRequest(BaseModel):
    id_token: str
    name: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"

@router.post("/google", response_model=AuthResponse)
async def authenticate_with_google(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user using Google OAuth token
    """
    try:
        # For now, we'll trust the token from frontend (in production, verify with Google)
        # In a real implementation, you'd verify the ID token with Google's API
        
        # Check if user exists
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Create new user
            user = User(
                name=request.name,
                email=request.email,
                google_id=request.id_token,  # Store Google user ID
                picture=request.picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update existing user with Google info if not present
            if not user.google_id:
                user.google_id = request.id_token
            if request.picture and not user.picture:
                user.picture = request.picture
            db.commit()
            db.refresh(user)
        
        # Create a simple access token (in production, use JWT)
        access_token = f"token_{user.id}_{request.id_token[:20]}"
        
        return AuthResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user
    """
    # Simple token validation (in production, use proper JWT verification)
    if not token.credentials.startswith("token_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Extract user ID from token
    try:
        user_id = token.credentials.split("_")[1]
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return UserResponse.model_validate(user)
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
