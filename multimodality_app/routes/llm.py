"""
LLM inference API routes.

Handles all AI processing and analysis endpoints for text and multimodal content.
Uses standardized response models from schema.py for consistency.
"""

import base64

from fastapi import APIRouter, File, UploadFile

from ..config import (
    DEFAULT_AUDIO_PROMPT,
    DEFAULT_IMAGE_PROMPT,
    DEFAULT_MULTIMODAL_PROMPT,
    DEFAULT_VIDEO_PROMPT,
)
from ..llm import get_response
from ..media_processing import process_uploaded_video
from ..schema import LLM
from .utils import (
    handle_processing_error,
    log_llm_response,
    log_multimodal_response,
    log_processing_start,
    log_upload_info,
    process_multimodal_files,
    process_single_file,
)

router = APIRouter()


@router.post("/api/invoke-text", response_model=LLM.Response.Text)
async def invoke_text(request: LLM.Request.Text):
    """Invoke LLM with text input for analysis."""
    try:
        log_processing_start("text analysis", "text_input", len(request.text.encode()))

        # Get LLM response for text
        analysis = get_response(text_input=request.text + "\n\n" + request.prompt)

        # Log with output preview
        log_llm_response("text analysis", "text_input", analysis.content, len(request.text.encode()))

        return LLM.Response.Text(
            status="success",
            message="Text analyzed successfully",
            content_type="text/plain",
            size_bytes=len(request.text.encode()),
            analysis=analysis.content,
        )
    except Exception as e:
        raise handle_processing_error("Text analysis", e)


@router.post("/api/invoke-audio", response_model=LLM.Response.Audio)
async def invoke_audio(audio: UploadFile = File(...), prompt: str = DEFAULT_AUDIO_PROMPT):
    """Upload audio file and invoke LLM for analysis."""
    try:
        audio_b64, size_bytes = await process_single_file(audio, "audio", "audio analysis with LLM")

        log_processing_start("audio analysis", audio.filename, size_bytes)

        # Get LLM analysis
        analysis = get_response(audio_b64s=[audio_b64], text_input=prompt)

        # Log with output preview
        log_llm_response("audio analysis", audio.filename, analysis.content, size_bytes)

        return LLM.Response.Audio(
            status="success",
            message="Audio analyzed successfully",
            transcription=analysis.content,
            size_bytes=size_bytes,
        )
    except Exception as e:
        raise handle_processing_error("Audio analysis", e)


@router.post("/api/invoke-image", response_model=LLM.Response.Image)
async def invoke_image(image: UploadFile = File(...), prompt: str = DEFAULT_IMAGE_PROMPT):
    """Upload image file and invoke LLM for analysis."""
    try:
        image_b64, size_bytes = await process_single_file(image, "image", "image analysis with LLM")

        log_processing_start("image analysis", image.filename, size_bytes)

        # Get LLM analysis
        analysis = get_response(image_b64s=[image_b64], text_input=prompt)

        # Log with output preview
        log_llm_response("image analysis", image.filename, analysis.content, size_bytes)

        return LLM.Response.Image(
            status="success",
            message="Image analyzed successfully",
            content_type="image",
            size_bytes=size_bytes,
            analysis=analysis.content,
        )
    except Exception as e:
        raise handle_processing_error("Image analysis", e)


@router.post("/api/invoke-video", response_model=LLM.Response.Video)
async def invoke_video(video: UploadFile = File(...), prompt: str = DEFAULT_VIDEO_PROMPT):
    """Upload video file and invoke LLM for analysis."""
    try:
        # Use direct processing for video to maintain video_info
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video analysis with LLM")
        log_processing_start("video analysis", video.filename, len(video_data))

        # Encode video with Gemini-safe processing
        video_b64, encoding_info = process_uploaded_video(video_data, video.filename)

        # Get LLM analysis
        analysis = get_response(video_b64s=[video_b64], text_input=prompt)

        # Log with output preview
        log_llm_response("video analysis", video.filename, analysis.content, len(video_data))

        return LLM.Response.Video(
            status="success",
            message="Video analyzed successfully",
            content_type="video",
            size_bytes=len(video_data),
            analysis=analysis.content,
        )
    except Exception as e:
        raise handle_processing_error("Video analysis", e)


@router.post("/api/invoke-video-base64", response_model=LLM.Response.Video)
async def invoke_video_base64(request: LLM.Request.VideoBase64):
    """Invoke LLM with base64 video data for analysis."""
    try:
        # Decode base64 to get video data
        video_data = base64.b64decode(request.video_b64)
        log_upload_info(request.filename, len(video_data), "base64 video analysis with LLM")
        log_processing_start("base64 video analysis", request.filename, len(video_data))

        # Encode video with Gemini-safe processing
        video_b64, encoding_info = process_uploaded_video(video_data, request.filename)

        # Get LLM analysis
        analysis = get_response(video_b64s=[video_b64], text_input=request.prompt)

        # Log with output preview
        log_llm_response("base64 video analysis", request.filename, analysis.content, len(video_data))

        return LLM.Response.Video(
            status="success",
            message="Base64 video analyzed successfully",
            content_type="video",
            size_bytes=len(video_data),
            analysis=analysis.content,
        )
    except Exception as e:
        raise handle_processing_error("Base64 video analysis", e)


@router.post("/api/invoke-multimodal", response_model=LLM.Response.Multimodal)
async def invoke_multimodal(
    prompt: str = DEFAULT_MULTIMODAL_PROMPT,
    audio: UploadFile = File(None),
    image: UploadFile = File(None),
    video: UploadFile = File(None),
):
    """Upload multiple media files and invoke LLM for multimodal analysis."""
    try:
        result = await process_multimodal_files(audio, image, video, "multimodal analysis with LLM")

        log_processing_start("multimodal analysis", "multimodal_content", result["total_size"])

        # Get LLM analysis with all media
        analysis = get_response(
            text_input=prompt,
            audio_b64s=[result["audio_b64"]] if result["audio_b64"] else None,
            image_b64s=[result["image_b64"]] if result["image_b64"] else None,
            video_b64s=[result["video_b64"]] if result["video_b64"] else None,
        )

        # Log with output preview
        log_multimodal_response("multimodal analysis", result["content_types"], analysis.content, result["total_size"])

        return LLM.Response.Multimodal(
            status="success",
            message="Multimodal content analyzed successfully",
            content_type="multimodal",
            size_bytes=result["total_size"],
            analysis=analysis.content,
        )
    except Exception as e:
        raise handle_processing_error("Multimodal analysis", e)
