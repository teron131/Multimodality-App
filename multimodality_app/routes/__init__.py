"""
API route modules for multimodal processing.

Exports all route handlers for the FastAPI application.
"""

from .audio import router as audio_router
from .image import router as image_router
from .main import router as main_router
from .multimodal import router as multimodal_router
from .realtime import router as realtime_router
from .video import router as video_router

__all__ = [
    "main_router",
    "audio_router",
    "image_router",
    "video_router",
    "multimodal_router",
    "realtime_router",
]
