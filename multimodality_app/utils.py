import base64
from pathlib import Path

import ffmpeg

SUPPORTED_IMAGE_FORMATS = {".png", ".jpeg", ".jpg", ".webp", ".heic", ".heif"}
SUPPORTED_AUDIO_FORMATS = {".wav", ".mp3", ".aiff", ".aac", ".ogg", ".flac"}


def encode_image(image_path: str | Path) -> str:
    """Convert image file to base64-encoded string.

    Args:
        image_path: Path to the input image file

    Returns:
        Base64-encoded image data as string

    Raises:
        ValueError: If image format is not supported
    """
    image_path = Path(image_path)

    if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(f"Unsupported image format: {image_path.suffix}. Supported formats: PNG, JPEG, WEBP, HEIC, HEIF")

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def encode_audio(audio_path: str | Path) -> str:
    """Convert audio file to base64-encoded audio data.

    Handles supported Gemini audio formats directly (WAV, MP3, AIFF, AAC, OGG, FLAC),
    converts other formats to MP3 in memory using ffmpeg, then returns base64-encoded audio data.

    Args:
        audio_path: Path to the input audio file

    Returns:
        Base64-encoded audio data as string
    """
    audio_path = Path(audio_path)

    if audio_path.suffix.lower() in SUPPORTED_AUDIO_FORMATS:
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()
    else:
        # Convert other formats to MP3 in memory
        try:
            out, err = ffmpeg.input(str(audio_path)).output("pipe:", format="mp3", acodec="libmp3lame", audio_bitrate="192k").run(capture_stdout=True, capture_stderr=True)
            audio_data = out
        except ffmpeg.Error as e:
            raise RuntimeError(f"FFmpeg conversion failed: {e.stderr.decode() if e.stderr else str(e)}") from e

    # Encode to base64
    return base64.b64encode(audio_data).decode("utf-8")
