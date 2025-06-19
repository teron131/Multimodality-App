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
from pydantic import BaseModel

from ..media_processing import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    SUPPORTED_IMAGE_FORMATS,
    VIDEO_MIME_TYPES,
    process_uploaded_audio,
    process_uploaded_image,
    process_uploaded_video,
)
from ..media_processing.video import get_video_info
from ..schema import AudioUploadResponse, ImageUploadResponse, VideoUploadResponse
from .utils import handle_processing_error, log_upload_info, validate_file_upload

router = APIRouter()


# Request/Response Models
class VideoBase64Request(BaseModel):
    video_b64: str
    filename: str


class VideoInfoResponse(BaseModel):
    status: str
    message: str
    video_info: dict
    size_bytes: int


class MultimodalEncodeResponse(BaseModel):
    status: str
    message: str
    audio_b64: str = None
    image_b64: str = None
    video_b64: str = None
    total_size_bytes: int
    content_types: list[str]


# =============================================================================
# AUDIO PROCESSING ENDPOINTS
# =============================================================================


@router.post("/api/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(audio: UploadFile = File(...)):
    """Upload and encode audio file."""
    validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

    try:
        # Read uploaded file
        audio_data = await audio.read()
        log_upload_info(audio.filename, len(audio_data), "audio upload")

        # Process audio encoding
        audio_b64 = process_uploaded_audio(audio_data, audio.filename)

        return AudioUploadResponse(
            status="success",
            message="Audio processed successfully",
            audio_b64=audio_b64,
            size_bytes=len(audio_data),
        )

    except Exception as e:
        raise handle_processing_error("Audio upload", e)


@router.post("/api/encode-audio", response_model=AudioUploadResponse)
async def encode_audio_endpoint(audio: UploadFile = File(...)):
    """Encode uploaded audio file to base64."""
    validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

    try:
        # Read uploaded file
        audio_data = await audio.read()
        log_upload_info(audio.filename, len(audio_data), "audio encoding")

        # Process audio encoding
        audio_b64 = process_uploaded_audio(audio_data, audio.filename)

        return AudioUploadResponse(
            status="success",
            message="Audio encoded successfully",
            audio_b64=audio_b64,
            size_bytes=len(audio_data),
        )

    except Exception as e:
        raise handle_processing_error("Audio encoding", e)


# =============================================================================
# IMAGE PROCESSING ENDPOINTS
# =============================================================================


@router.post("/api/upload-image", response_model=ImageUploadResponse)
async def upload_image(image: UploadFile = File(...)):
    """Upload and encode image file."""
    validate_file_upload(image.filename, image.content_type, IMAGE_MIME_TYPES)

    try:
        # Read uploaded file
        image_data = await image.read()
        log_upload_info(image.filename, len(image_data), "image upload")

        # Process image encoding
        image_b64 = process_uploaded_image(image_data, image.filename)

        return ImageUploadResponse(
            status="success",
            message="Image processed successfully",
            image_b64=image_b64,
            size_bytes=len(image_data),
        )

    except Exception as e:
        raise handle_processing_error("Image upload", e)


@router.post("/api/encode-image", response_model=ImageUploadResponse)
async def encode_image_endpoint(image: UploadFile = File(...)):
    """Encode uploaded image file to base64."""
    validate_file_upload(image.filename, image.content_type, IMAGE_MIME_TYPES)

    try:
        # Read uploaded file
        image_data = await image.read()
        log_upload_info(image.filename, len(image_data), "image encoding")

        # Process image encoding
        image_b64 = process_uploaded_image(image_data, image.filename)

        return ImageUploadResponse(
            status="success",
            message="Image encoded successfully",
            image_b64=image_b64,
            size_bytes=len(image_data),
        )

    except Exception as e:
        raise handle_processing_error("Image encoding", e)


# =============================================================================
# VIDEO PROCESSING ENDPOINTS
# =============================================================================


@router.post("/api/upload-video", response_model=VideoUploadResponse)
async def upload_video(video: UploadFile = File(...)):
    """Upload and process video file for encoding."""
    validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

    try:
        # Read uploaded file
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video upload")

        # Process video encoding
        video_b64, video_info = process_uploaded_video(video_data, video.filename)

        return VideoUploadResponse(
            status="success",
            message="Video processed successfully",
            video_b64=video_b64,
            video_info=video_info,
            size_bytes=len(video_data),
        )

    except Exception as e:
        raise handle_processing_error("Video upload", e)


@router.post("/api/encode-video", response_model=VideoUploadResponse)
async def encode_video_endpoint(video: UploadFile = File(...)):
    """Encode uploaded video file to base64."""
    validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

    try:
        # Read uploaded file
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video encoding")

        # Process video encoding
        video_b64, video_info = process_uploaded_video(video_data, video.filename)

        return VideoUploadResponse(
            status="success",
            message="Video encoded successfully",
            video_b64=video_b64,
            video_info=video_info,
            size_bytes=len(video_data),
        )

    except Exception as e:
        raise handle_processing_error("Video encoding", e)


@router.post("/api/encode-video-base64", response_model=VideoUploadResponse)
async def encode_video_base64(request: VideoBase64Request):
    """Process base64 video data and re-encode for optimization."""
    try:
        # Decode base64 to get video data
        video_data = base64.b64decode(request.video_b64)
        log_upload_info(request.filename, len(video_data), "base64 video encoding")

        # Process video encoding
        video_b64, video_info = process_uploaded_video(video_data, request.filename)

        return VideoUploadResponse(
            status="success",
            message="Base64 video encoded successfully",
            video_b64=video_b64,
            video_info=video_info,
            size_bytes=len(video_data),
        )

    except Exception as e:
        raise handle_processing_error("Base64 video encoding", e)


@router.post("/api/video-info", response_model=VideoInfoResponse)
async def get_video_info_endpoint(video: UploadFile = File(...)):
    """Get video information without processing."""
    validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

    try:
        # Read uploaded file
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video info")

        # Save to temporary file for info extraction
        temp_file = Path(tempfile.mktemp(suffix=Path(video.filename).suffix or ".mp4"))

        try:
            with open(temp_file, "wb") as f:
                f.write(video_data)

            # Get video info
            video_info = get_video_info(temp_file)

        finally:
            if temp_file.exists():
                temp_file.unlink()

        return VideoInfoResponse(
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


@router.post("/api/encode-multimodal", response_model=MultimodalEncodeResponse)
async def encode_multimodal_files(audio: UploadFile = File(None), image: UploadFile = File(None), video: UploadFile = File(None)):
    """Encode multiple media files to base64 without LLM inference."""
    if not any([audio, image, video]):
        raise HTTPException(status_code=400, detail="At least one file (audio, image, or video) must be provided")

    try:
        audio_b64 = None
        image_b64 = None
        video_b64 = None
        total_size = 0
        content_types = []

        # Process audio if provided
        if audio and audio.filename:
            validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

            audio_data = await audio.read()
            total_size += len(audio_data)
            content_types.append("audio")

            # Process audio encoding
            audio_b64 = process_uploaded_audio(audio_data, audio.filename)
            log_upload_info(audio.filename, len(audio_data), "multimodal audio encoding")

        # Process image if provided
        if image and image.filename:
            # Validate image file type
            file_ext = Path(image.filename).suffix.lower()
            if file_ext not in SUPPORTED_IMAGE_FORMATS:
                raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

            image_data = await image.read()
            total_size += len(image_data)
            content_types.append("image")

            # Process image encoding
            image_b64 = process_uploaded_image(image_data, image.filename)
            log_upload_info(image.filename, len(image_data), "multimodal image encoding")

        # Process video if provided
        if video and video.filename:
            validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

            video_data = await video.read()
            total_size += len(video_data)
            content_types.append("video")

            # Process video encoding
            video_b64, _ = process_uploaded_video(video_data, video.filename)
            log_upload_info(video.filename, len(video_data), "multimodal video encoding")

        content_type_str = " + ".join(content_types)

        return MultimodalEncodeResponse(
            status="success",
            message=f"Multimodal encoding successful ({content_type_str})",
            audio_b64=audio_b64,
            image_b64=image_b64,
            video_b64=video_b64,
            total_size_bytes=total_size,
            content_types=content_types,
        )

    except Exception as e:
        raise handle_processing_error("Multimodal encoding", e)
