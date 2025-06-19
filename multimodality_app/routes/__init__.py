"""
API route modules for multimodal processing.

Clean Architecture:
- main.py: System configuration, health checks, static files
- llm.py: All LLM inference endpoints (process-*-unified)
- processing.py: Unified media encoding endpoints
- realtime.py: WebSocket streaming endpoints

Exports all route handlers for the FastAPI application.
"""

from .llm import router as llm_router
from .main import router as main_router
from .processing import router as processing_router
from .realtime import router as realtime_router

__all__ = [
    "main_router",  # System configuration + health checks
    "llm_router",  # LLM inference endpoints
    "processing_router",  # Unified media encoding
    "realtime_router",  # WebSocket streaming
]
