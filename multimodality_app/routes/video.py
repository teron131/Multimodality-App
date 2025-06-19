"""
Video processing API endpoints.

Handles video file uploads and unified video processing with LLM analysis.
"""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import DEFAULT_VIDEO_PROMPT
from ..llm import get_response
from ..media_processing import VIDEO_MIME_TYPES, process_uploaded_video
from ..schema import MultimodalResponse, UploadResponse
from .utils import handle_processing_error, log_upload_info, validate_file_upload

router = APIRouter()


class VideoUploadResponse(UploadResponse):
    """Video upload response with base64 data."""

    video_b64: str
    video_info: dict


@router.post("/api/upload-video", response_model=VideoUploadResponse)
async def upload_video(video: UploadFile = File(...)):
    """Upload and process video file."""
    validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

    try:
        # Read uploaded file
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video upload")

        # Process video (save → encode → cleanup)
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


@router.post("/api/process-video-unified", response_model=MultimodalResponse)
async def process_video_unified(video: UploadFile = File(...), prompt: str = DEFAULT_VIDEO_PROMPT):
    """Unified endpoint: upload video → process → get LLM response in one call."""
    validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

    try:
        # Read uploaded file
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "unified video processing")

        # Process video (save → encode → cleanup)
        video_b64, video_info = process_uploaded_video(video_data, video.filename)

        # Use LLM module for processing with video_b64
        response = get_response(text_input=prompt, video_b64s=[video_b64])

        return MultimodalResponse(
            status="success",
            message="Video processed successfully",
            analysis=response.content,
            content_type="video",
            size_bytes=len(video_data),
        )

    except Exception as e:
        raise handle_processing_error("Unified video processing", e)
