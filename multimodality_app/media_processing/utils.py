"""
Media format validation and constants.

Defines supported formats and provides validation utilities for media files.
"""

from pathlib import Path

# Gemini-supported image formats
SUPPORTED_IMAGE_FORMATS = {".png", ".jpeg", ".jpg", ".webp", ".heic", ".heif"}

# Gemini-supported audio formats (can be sent directly)
SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".aiff", ".aac", ".ogg", ".flac"}

# Additional formats that can be converted
ADDITIONAL_AUDIO_FORMATS = {".webm", ".m4a"}
ALL_AUDIO_FORMATS = SUPPORTED_AUDIO_FORMATS | ADDITIONAL_AUDIO_FORMATS

# Gemini-supported video formats
SUPPORTED_VIDEO_FORMATS = {".mp4", ".mpeg", ".mov", ".avi", ".flv", ".mpg", ".webm", ".wmv", ".3gp"}

# MIME type mappings for web uploads
IMAGE_MIME_MAPPINGS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

AUDIO_MIME_MAPPINGS = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/mp3": ".mp3",
    "audio/mpeg": ".mp3",
    "audio/flac": ".flac",
    "audio/ogg": ".ogg",
    "audio/m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/aiff": ".aiff",
}

VIDEO_MIME_MAPPINGS = {
    "video/mp4": ".mp4",
    "video/mpeg": ".mpeg",
    "video/mov": ".mov",
    "video/avi": ".avi",
    "video/x-flv": ".flv",
    "video/mpg": ".mpg",
    "video/webm": ".webm",
    "video/wmv": ".wmv",
    "video/3gpp": ".3gp",
}

# MIME type sets for validation (used by validate_file_upload)
AUDIO_MIME_TYPES = set(AUDIO_MIME_MAPPINGS.keys())
IMAGE_MIME_TYPES = set(IMAGE_MIME_MAPPINGS.keys())
VIDEO_MIME_TYPES = set(VIDEO_MIME_MAPPINGS.keys())


def is_image_format_supported(file_path: str | Path) -> bool:
    """Check if an image file format is supported."""
    return Path(file_path).suffix.lower() in SUPPORTED_IMAGE_FORMATS


def is_audio_format_supported(file_path: str | Path) -> bool:
    """Check if an audio file format is supported."""
    return Path(file_path).suffix.lower() in ALL_AUDIO_FORMATS


def is_video_format_supported(file_path: str | Path) -> bool:
    """Check if a video file format is supported."""
    return Path(file_path).suffix.lower() in SUPPORTED_VIDEO_FORMATS
