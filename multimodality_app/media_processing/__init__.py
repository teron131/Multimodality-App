"""
Multimodal AI media processing modules.

Unified approach: All video processing uses Gemini-safe encoding for maximum compatibility.
"""

# Audio processing
from .audio import encode_audio, encode_raw_audio, process_uploaded_audio

# Image processing
from .image import encode_image, process_uploaded_image

# Format validation utilities
from .utils import (
    ALL_AUDIO_FORMATS,
    AUDIO_MIME_MAPPINGS,
    AUDIO_MIME_TYPES,
    IMAGE_MIME_MAPPINGS,
    IMAGE_MIME_TYPES,
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_VIDEO_FORMATS,
    VIDEO_MIME_MAPPINGS,
    VIDEO_MIME_TYPES,
    is_audio_format_supported,
    is_image_format_supported,
    is_video_format_supported,
)

# Video processing (unified Gemini-safe)
from .video import encode_video, process_uploaded_video

__all__ = [
    # Processing functions
    "process_uploaded_audio",
    "process_uploaded_image",
    "process_uploaded_video",
    # Individual encoding functions
    "encode_audio",
    "encode_raw_audio",
    "encode_image",
    "encode_video",
    # Format constants
    "SUPPORTED_IMAGE_FORMATS",
    "SUPPORTED_AUDIO_FORMATS",
    "SUPPORTED_VIDEO_FORMATS",
    "ALL_AUDIO_FORMATS",
    # MIME type mappings and sets
    "IMAGE_MIME_TYPES",
    "AUDIO_MIME_TYPES",
    "VIDEO_MIME_TYPES",
    "IMAGE_MIME_MAPPINGS",
    "AUDIO_MIME_MAPPINGS",
    "VIDEO_MIME_MAPPINGS",
    # Validation functions
    "is_image_format_supported",
    "is_audio_format_supported",
    "is_video_format_supported",
]
