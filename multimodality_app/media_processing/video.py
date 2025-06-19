"""
Video processing and encoding for multimodal AI.

Handles video file optimization, metadata extraction, and base64 encoding for LLM consumption.
"""

import base64
import logging
import tempfile
from pathlib import Path

import ffmpeg

logger = logging.getLogger(__name__)


def encode_video(video_path: str | Path) -> str:
    """Convert video file to base64-encoded video data optimized for Gemini.

    Optimizes all video files for Gemini processing by:
    - Converting to MP4 format for consistent compatibility
    - Using reasonable compression settings for API transmission
    - Maintaining quality while reducing file size

    Args:
        video_path: Path to the input video file

    Returns:
        Base64-encoded optimized video data as string
    """
    video_path = Path(video_path)
    logger.info(f"🎬 Encoding video file: {video_path}")

    # Always optimize video for Gemini API
    try:
        logger.debug("🔄 Starting FFmpeg video optimization...")
        out, err = (
            ffmpeg.input(str(video_path))
            .output("pipe:", format="mp4", vcodec="libx264", acodec="aac", preset="medium", crf=28, movflags="frag_keyframe+empty_moov")
            .run(capture_stdout=True, capture_stderr=True)
        )  # H.264 codec for wide compatibility  # AAC audio codec  # Balance between compression and speed  # Constant Rate Factor for good quality/size balance  # Optimize for streaming
        video_data = out
        logger.info(f"✅ FFmpeg optimization successful: {len(video_data)} bytes")
    except ffmpeg.Error as e:
        error_msg = f"FFmpeg video optimization failed: {e.stderr.decode() if e.stderr else str(e)}"
        logger.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg) from e

    # Encode to base64
    b64_data = base64.b64encode(video_data).decode("utf-8")
    logger.info(f"✅ Video encoding complete: {len(video_data)} bytes → {len(b64_data)} chars base64")
    return b64_data


def get_video_info(video_path: str | Path) -> dict:
    """Get video file information including size and duration.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with file_size_mb and duration_seconds
    """
    video_path = Path(video_path)
    logger.debug(f"📊 Getting video info for: {video_path}")

    # Get file size
    file_size_bytes = video_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)

    # Get duration using ffprobe
    try:
        probe = ffmpeg.probe(str(video_path))
        duration_seconds = float(probe["streams"][0]["duration"])
        logger.debug(f"✅ Video info extracted: {file_size_mb:.2f}MB, {duration_seconds:.2f}s")
    except (ffmpeg.Error, KeyError, ValueError) as e:
        # Fallback if duration can't be determined
        duration_seconds = 0
        logger.warning(f"⚠️ Could not determine video duration: {e}")

    info = {"file_size_mb": file_size_mb, "duration_seconds": duration_seconds}
    logger.info(f"📊 Video info: {info}")
    return info


def process_uploaded_video(video_data: bytes, filename: str) -> tuple[str, dict]:
    """Complete video processing workflow: save → optimize → get info → cleanup.

    Args:
        video_data: Raw video bytes from upload
        filename: Original filename to determine format

    Returns:
        Tuple of (base64_encoded_video, video_info)
    """
    logger.info(f"📤 Processing uploaded video: {filename} ({len(video_data)} bytes)")

    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".mp4"))
    logger.debug(f"📁 Creating temporary file: {temp_file}")

    try:
        with open(temp_file, "wb") as f:
            f.write(video_data)

        # Get video information before optimization
        video_info = get_video_info(temp_file)

        # Optimize and convert to base64
        video_b64 = encode_video(temp_file)

        logger.info(f"✅ Video upload processing complete: {len(video_b64)} chars base64")
        return video_b64, video_info

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"🗑️ Cleaned up temporary file: {temp_file}")
