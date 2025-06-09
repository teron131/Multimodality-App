from pathlib import Path

# Gemini-supported image formats
SUPPORTED_IMAGE_FORMATS = {".png", ".jpeg", ".jpg", ".webp", ".heic", ".heif"}

# Gemini-supported audio formats (can be sent directly)
SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".aiff", ".aac", ".ogg", ".flac"}

# Additional formats that can be converted
ADDITIONAL_AUDIO_FORMATS = {".webm", ".m4a"}
ALL_AUDIO_FORMATS = SUPPORTED_AUDIO_FORMATS | ADDITIONAL_AUDIO_FORMATS

# MIME type mappings for web uploads
IMAGE_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

AUDIO_MIME_TYPES = {
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


def is_image_format_supported(file_path: str | Path) -> bool:
    """Check if an image file format is supported."""
    return Path(file_path).suffix.lower() in SUPPORTED_IMAGE_FORMATS


def is_audio_format_supported(file_path: str | Path) -> bool:
    """Check if an audio file format is supported."""
    return Path(file_path).suffix.lower() in ALL_AUDIO_FORMATS
