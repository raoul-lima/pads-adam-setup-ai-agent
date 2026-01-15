"""
API Routes Package
==================
Modular route organization for the Adam Setup Multi-Agent API.

This package contains separate route modules for different API domains:
- chat: Conversation and message handling
- feedback: User feedback management
- data: Data operations (CSV preview, etc.)
- health: Health checks and system information
"""

from .chat import router as chat_router
from .feedback import router as feedback_router
from .data import router as data_router
from .health import router as health_router

__all__ = [
    "chat_router",
    "feedback_router",
    "data_router"
    "health_router"
]

