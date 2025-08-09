from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.logging import setup_logging
from app.api import onboarding, chat, approvals, auth

# Setup logging
setup_logging()

app = FastAPI(
    title=settings.app_name,
    description="An autonomous, multi-modal onboarding agent",
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(chat.router)
app.include_router(approvals.router)

@app.get("/")
async def root():
    return {"message": "Aura Onboarding Agent API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "aura-onboarding-agent",
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)