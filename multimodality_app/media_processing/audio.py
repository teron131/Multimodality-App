import base64
import tempfile
from pathlib import Path

import ffmpeg

from .utils import SUPPORTED_AUDIO_FORMATS


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


def process_uploaded_audio(audio_data: bytes, filename: str) -> str:
    """Complete audio processing workflow: save → convert → cleanup.

    Args:
        audio_data: Raw audio bytes from upload
        filename: Original filename to determine format

    Returns:
        Base64-encoded audio data ready for Gemini API
    """
    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".webm"))

    try:
        with open(temp_file, "wb") as f:
            f.write(audio_data)

        # Convert to base64 (handles all format conversion automatically)
        return encode_audio(temp_file)

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
