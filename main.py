#!/usr/bin/env python3
"""
Whook - Webhook Manager
Main application entry point
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import asyncio

from app.core.config import settings
from app.routes import auth_router, webhooks_router, websocket_router
from app.routes.websocket import redis_listener

# Initialize FastAPI app
app = FastAPI(
    title="Whook - Webhook Manager",
    description="High-performance webhook management system",
    version="2.0.0"
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(webhooks_router, tags=["Webhooks"])
app.include_router(websocket_router, tags=["WebSocket"])


@app.on_event("startup")
async def startup_event():
    """Start the Redis listener on app startup"""
    asyncio.create_task(redis_listener())
    print("✅ Application started successfully")
    print(f"📍 Server running on http://{settings.APP_HOST}:{settings.APP_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 Application shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
