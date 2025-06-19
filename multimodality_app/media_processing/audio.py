"""
Audio processing and encoding for multimodal AI.

Handles audio file conversion, optimization, and base64 encoding for LLM consumption.
"""

import base64
import logging
import struct
import tempfile
import wave
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


def pcm_to_wav(pcm_data: bytes) -> bytes:
    """Convert raw PCM data to WAV format.

    Args:
        pcm_data: Raw PCM audio data

    Returns:
        WAV file data as bytes
    """
    logger.debug(f"🎵 Converting {len(pcm_data)} bytes of PCM data to WAV format")

    # Create WAV file in memory
    with tempfile.NamedTemporaryFile() as temp_wav:
        with wave.open(temp_wav.name, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)

        # Read the WAV file data
        temp_wav.seek(0)
        wav_data = temp_wav.read()

    logger.debug(f"✅ PCM to WAV conversion complete: {len(wav_data)} bytes")
    return wav_data


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
    logger.info(f"🎵 Encoding audio file: {audio_path}")

    # Always optimize audio for Gemini, even if format is supported
    try:
        logger.debug(f"🔧 Running FFmpeg optimization: mono, 32k bitrate, 16kHz sample rate")
        out, err = (
            ffmpeg.input(str(audio_path)).output("pipe:", format="mp3", acodec="libmp3lame", audio_bitrate="32k", ac=1, ar=16000).run(capture_stdout=True, capture_stderr=True)
        )  # Low bitrate since Gemini downsamples to 16 Kbps  # Convert to mono (single channel)  # Reasonable sample rate for speech
        audio_data = out
        logger.debug(f"✅ FFmpeg processing complete: {len(audio_data)} bytes")
    except ffmpeg.Error as e:
        error_msg = f"FFmpeg optimization failed: {e.stderr.decode() if e.stderr else str(e)}"
        logger.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg) from e

    # Encode to base64
    b64_data = base64.b64encode(audio_data).decode("utf-8")
    logger.info(f"✅ Audio encoding successful: {len(b64_data)} chars base64")
    return b64_data


def encode_raw_audio(audio_data: bytes) -> str:
    """Convert raw PCM audio data to base64-encoded audio optimized for Gemini.

    This function is specifically designed for WebSocket real-time audio data.

    Args:
        audio_data: Raw PCM audio data bytes

    Returns:
        Base64-encoded optimized audio data as string
    """
    logger.info(f"🎵 Processing raw audio data: {len(audio_data)} bytes")

    # Convert PCM to WAV format
    wav_data = pcm_to_wav(audio_data)

    # Save to temporary file for FFmpeg processing
    temp_file = Path(tempfile.mktemp(suffix=".wav"))
    logger.debug(f"📁 Creating temporary WAV file: {temp_file}")

    try:
        with open(temp_file, "wb") as f:
            f.write(wav_data)

        # Use existing encode_audio function
        result = encode_audio(temp_file)
        logger.info(f"✅ Raw audio encoding successful: {len(result)} chars base64")
        return result

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"🗑️ Cleaned up temporary file: {temp_file}")


def process_uploaded_audio(audio_data: bytes, filename: str) -> str:
    """Complete audio processing workflow: save → optimize → cleanup.

    Args:
        audio_data: Raw audio bytes from upload
        filename: Original filename to determine format

    Returns:
        Base64-encoded optimized audio data ready for Gemini API
    """
    logger.info(f"📤 Processing uploaded audio: {filename} ({len(audio_data)} bytes)")

    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".webm"))
    logger.debug(f"📁 Creating temporary file: {temp_file}")

    try:
        with open(temp_file, "wb") as f:
            f.write(audio_data)

        # Optimize and convert to base64 (always processes for optimal compression)
        result = encode_audio(temp_file)
        logger.info(f"✅ Upload processing complete: {len(result)} chars base64")
        return result

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"🗑️ Cleaned up temporary file: {temp_file}")
