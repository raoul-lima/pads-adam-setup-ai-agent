"""
Health Check Routes
==================
"""

from fastapi import APIRouter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Health"],
)


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "evaluation-api",
        "timestamp": datetime.now().isoformat()
    }

