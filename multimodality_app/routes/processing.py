"""
Media processing API routes.

Unified endpoint collection for audio, image, video, and multimodal file processing.
Handles upload, encoding, and base64 conversion without LLM inference.
LLM inference is handled in llm.py routes.
"""

import base64
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..media_processing import SUPPORTED_IMAGE_FORMATS, process_uploaded_video
from ..media_processing.video import get_video_info
from ..schema import Media
from .utils import (
    handle_processing_error,
    log_upload_info,
    process_multimodal_files,
    process_single_file,
)

router = APIRouter()


# =============================================================================
# SINGLE MEDIA PROCESSING ENDPOINTS
# =============================================================================


@router.post("/api/encode-audio", response_model=Media.Audio)
async def encode_audio_endpoint(audio: UploadFile = File(...)):
    """Encode uploaded audio file to base64."""
    audio_b64, size_bytes = await process_single_file(audio, "audio", "audio encoding")

    return Media.Audio(
        status="success",
        message="Audio encoded successfully",
        audio_b64=audio_b64,
        audio_info={},  # Add empty dict for consistency with schema
        size_bytes=size_bytes,
    )


@router.post("/api/encode-image", response_model=Media.Image)
async def encode_image_endpoint(image: UploadFile = File(...)):
    """Encode uploaded image file to base64."""
    image_b64, size_bytes = await process_single_file(image, "image", "image encoding")

    return Media.Image(
        status="success",
        message="Image encoded successfully",
        image_b64=image_b64,
        image_info={},  # Add empty dict for consistency with schema
        size_bytes=size_bytes,
    )


@router.post("/api/encode-video", response_model=Media.Video)
async def encode_video_endpoint(video: UploadFile = File(...)):
    """Encode uploaded video file to base64."""
    try:
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video encoding")

        video_b64, video_info = process_uploaded_video(video_data, video.filename)

        return Media.Video(
            status="success",
            message="Video encoded successfully",
            video_b64=video_b64,
            video_info=video_info,
            size_bytes=len(video_data),
        )
    except Exception as e:
        raise handle_processing_error("Video encoding", e)


@router.post("/api/video-info", response_model=Media.VideoInfo)
async def get_video_info_endpoint(video: UploadFile = File(...)):
    """Get video information without processing."""
    try:
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video info")

        # Save to temporary file for info extraction
        temp_file = Path(tempfile.mktemp(suffix=Path(video.filename).suffix or ".mp4"))

        try:
            with open(temp_file, "wb") as f:
                f.write(video_data)

            video_info = get_video_info(temp_file)
        finally:
            if temp_file.exists():
                temp_file.unlink()

        return Media.VideoInfo(
            status="success",
            message="Video information extracted",
            video_info=video_info,
            size_bytes=len(video_data),
        )
    except Exception as e:
        raise handle_processing_error("Video info extraction", e)


# =============================================================================
# MULTIMODAL PROCESSING ENDPOINTS
# =============================================================================


@router.post("/api/encode-multimodal", response_model=Media.Multimodal)
async def encode_multimodal_files(
    audio: UploadFile = File(None),
    image: UploadFile = File(None),
    video: UploadFile = File(None),
):
    """Encode multiple media files to base64 without LLM inference."""
    # Additional validation for image formats (since process_multimodal_files doesn't handle this)
    if image and image.filename:
        file_ext = Path(image.filename).suffix.lower()
        if file_ext not in SUPPORTED_IMAGE_FORMATS:
            raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

    result = await process_multimodal_files(audio, image, video, "multimodal encoding")

    content_type_str = " + ".join(result["content_types"])

    return Media.Multimodal(
        status="success",
        message=f"Multimodal encoding successful ({content_type_str})",
        audio_b64=result["audio_b64"],
        image_b64=result["image_b64"],
        video_b64=result["video_b64"],
        total_size_bytes=result["total_size"],
        content_types=result["content_types"],
    )
