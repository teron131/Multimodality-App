import base64
import struct
import tempfile
import wave
from pathlib import Path

import ffmpeg


def pcm_to_wav(pcm_data: bytes) -> bytes:
    """Convert raw PCM data to WAV format.

    Args:
        pcm_data: Raw PCM audio data

    Returns:
        WAV file data as bytes
    """
    # Create WAV file in memory
    with tempfile.NamedTemporaryFile() as temp_wav:
        with wave.open(temp_wav.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)

        # Read the WAV file data
        temp_wav.seek(0)
        return temp_wav.read()


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
        out, err = (
            ffmpeg.input(str(audio_path)).output("pipe:", format="mp3", acodec="libmp3lame", audio_bitrate="32k", ac=1, ar=16000).run(capture_stdout=True, capture_stderr=True)
        )  # Low bitrate since Gemini downsamples to 16 Kbps  # Convert to mono (single channel)  # Reasonable sample rate for speech
        audio_data = out
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg optimization failed: {e.stderr.decode() if e.stderr else str(e)}") from e

    # Encode to base64
    return base64.b64encode(audio_data).decode("utf-8")


def encode_raw_audio(audio_data: bytes) -> str:
    """Convert raw PCM audio data to base64-encoded audio optimized for Gemini.

    This function is specifically designed for WebSocket real-time audio data.

    Args:
        audio_data: Raw PCM audio data bytes

    Returns:
        Base64-encoded optimized audio data as string
    """
    # Convert PCM to WAV format
    wav_data = pcm_to_wav(audio_data)

    # Save to temporary file for FFmpeg processing
    temp_file = Path(tempfile.mktemp(suffix=".wav"))

    try:
        with open(temp_file, "wb") as f:
            f.write(wav_data)

        # Use existing encode_audio function
        return encode_audio(temp_file)

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


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
