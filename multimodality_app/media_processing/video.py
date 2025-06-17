import base64
import tempfile
from pathlib import Path

import ffmpeg


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

    # Always optimize video for Gemini API
    try:
        out, err = ffmpeg.input(str(video_path)).output("pipe:", format="mp4", vcodec="libx264", acodec="aac", preset="medium", crf=28, movflags="frag_keyframe+empty_moov").run(capture_stdout=True, capture_stderr=True)  # H.264 codec for wide compatibility  # AAC audio codec  # Balance between compression and speed  # Constant Rate Factor for good quality/size balance  # Optimize for streaming
        video_data = out
    except ffmpeg.Error as e:
        raise RuntimeError(f"FFmpeg video optimization failed: {e.stderr.decode() if e.stderr else str(e)}") from e

    # Encode to base64
    return base64.b64encode(video_data).decode("utf-8")


def get_video_info(video_path: str | Path) -> dict:
    """Get video file information including size and duration.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with file_size_mb and duration_seconds
    """
    video_path = Path(video_path)

    # Get file size
    file_size_bytes = video_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)

    # Get duration using ffprobe
    try:
        probe = ffmpeg.probe(str(video_path))
        duration_seconds = float(probe["streams"][0]["duration"])
    except (ffmpeg.Error, KeyError, ValueError):
        # Fallback if duration can't be determined
        duration_seconds = 0

    return {"file_size_mb": file_size_mb, "duration_seconds": duration_seconds}


def process_uploaded_video(video_data: bytes, filename: str) -> tuple[str, dict]:
    """Complete video processing workflow: save → optimize → get info → cleanup.

    Args:
        video_data: Raw video bytes from upload
        filename: Original filename to determine format

    Returns:
        Tuple of (base64_encoded_video, video_info)
    """
    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".mp4"))

    try:
        with open(temp_file, "wb") as f:
            f.write(video_data)

        # Get video information before optimization
        video_info = get_video_info(temp_file)

        # Optimize and convert to base64
        video_base64 = encode_video(temp_file)

        return video_base64, video_info

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
