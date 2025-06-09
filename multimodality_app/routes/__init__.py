from .audio import router as audio_router
from .image import router as image_router
from .main import router as main_router
from .multimodal import router as multimodal_router

__all__ = [
    "main_router",
    "audio_router",
    "image_router",
    "multimodal_router",
]
