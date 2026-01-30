from fastapi import Request, HTTPException
from typing import Optional
from datetime import datetime
from app.models import User
from app.core import SessionLocal


def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session"""
    return request.session.get('user')


def require_auth(request: Request) -> dict:
    """Require authentication, raise exception if not authenticated"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_or_create_user(email: str, name: str, picture: str, google_id: str) -> User:
    """Get existing user or create new one"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if not user:
            user = User(
                email=email,
                name=name,
                picture=picture,
                google_id=google_id,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update last login
            user.last_login = datetime.utcnow()
            if name:
                user.name = name
            if picture:
                user.picture = picture
            db.commit()
        
        return user
    finally:
        db.close()
