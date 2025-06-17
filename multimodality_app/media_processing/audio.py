import base64
import tempfile
from pathlib import Path

import ffmpeg

from .utils import SUPPORTED_AUDIO_FORMATS


def encode_audio(audio_path: str | Path) -> str:
    """Convert audio file to base64-encoded audio data optimized for Gemini.

    Optimizes all audio files for Gemini processing by:
    - Converting to mono (single channel) since Gemini combines multiple channels anyway
    - Using low bitrate (32k) since Gemini downsamples to 16 Kbps
    - Converting to MP3 format for consistent compression

    Args:
        audio_path: Path to the input audio file

    Returns:
        Base64-encoded optimized audio data as string
    """
    audio_path = Path(audio_path)

    # Always optimize audio for Gemini, even if format is supported
    try:
        out, err = ffmpeg.input(str(audio_path)).output("pipe:", format="mp3", acodec="libmp3lame", audio_bitrate="32k", ac=1, ar=22050).run(capture_stdout=True, capture_stderr=True)  # Low bitrate since Gemini downsamples to 16 Kbps  # Convert to mono (single channel)  # Reasonable sample rate for speech
        audio_data = out
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg optimization failed: {e.stderr.decode() if e.stderr else str(e)}") from e

    # Encode to base64
    return base64.b64encode(audio_data).decode("utf-8")


def process_uploaded_audio(audio_data: bytes, filename: str) -> str:
    """Complete audio processing workflow: save → optimize → cleanup.

    Args:
        audio_data: Raw audio bytes from upload
        filename: Original filename to determine format

    Returns:
        Base64-encoded optimized audio data ready for Gemini API
    """
    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".webm"))

    try:
        with open(temp_file, "wb") as f:
            f.write(audio_data)

        # Optimize and convert to base64 (always processes for optimal compression)
        return encode_audio(temp_file)

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
