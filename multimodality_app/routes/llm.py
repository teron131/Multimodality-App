"""
LLM inference API routes.

Handles all AI processing and analysis endpoints for text and multimodal content.
Uses standardized response models from schema.py for consistency.
"""

import base64

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import (
    DEFAULT_AUDIO_PROMPT,
    DEFAULT_IMAGE_PROMPT,
    DEFAULT_MULTIMODAL_PROMPT,
    DEFAULT_VIDEO_PROMPT,
)
from ..llm import get_response
from ..media_processing import (
    process_uploaded_audio,
    process_uploaded_image,
    process_uploaded_video,
)
from ..media_processing.utils import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    VIDEO_MIME_TYPES,
)
from ..schema import MultimodalResponse, UnifiedProcessResponse
from .utils import handle_processing_error, log_upload_info, validate_file_upload

router = APIRouter()


class TextProcessRequest(BaseModel):
    text: str
    prompt: str = "Please analyze this text and provide insights."


class VideoBase64Request(BaseModel):
    video_b64: str
    filename: str
    prompt: str = DEFAULT_VIDEO_PROMPT


class MultimodalAnalysisRequest(BaseModel):
    audio_file: UploadFile = None
    image_file: UploadFile = None
    video_file: UploadFile = None
    prompt: str = DEFAULT_MULTIMODAL_PROMPT


@router.post("/api/process-text", response_model=MultimodalResponse)
async def process_text(request: TextProcessRequest):
    """Process text input directly with LLM."""
    try:
        # Get LLM response for text
        analysis = await get_response(text=request.text, prompt=request.prompt)

        return MultimodalResponse(
            status="success",
            message="Text processed successfully",
            content_type="text/plain",
            size_bytes=len(request.text.encode()),
            analysis=analysis,
        )
    except Exception as e:
        raise handle_processing_error("Text processing", e)


@router.post("/api/process-audio-unified", response_model=UnifiedProcessResponse)
async def process_audio_unified(audio: UploadFile = File(...), prompt: str = DEFAULT_AUDIO_PROMPT):
    """Upload audio file and analyze with LLM."""
    validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

    try:
        # Read and process audio
        audio_data = await audio.read()
        log_upload_info(audio.filename, len(audio_data), "audio processing with LLM")

        # Encode audio
        audio_b64 = process_uploaded_audio(audio_data, audio.filename)

        # Get LLM analysis
        analysis = await get_response(audio_b64=audio_b64, prompt=prompt)

        return UnifiedProcessResponse(
            status="success",
            message="Audio processed and analyzed successfully",
            transcription=analysis,
            size_bytes=len(audio_data),
        )
    except Exception as e:
        raise handle_processing_error("Audio processing with LLM", e)


@router.post("/api/process-image-unified", response_model=MultimodalResponse)
async def process_image_unified(image: UploadFile = File(...), prompt: str = DEFAULT_IMAGE_PROMPT):
    """Upload image file and analyze with LLM."""
    validate_file_upload(image.filename, image.content_type, IMAGE_MIME_TYPES)

    try:
        # Read and process image
        image_data = await image.read()
        log_upload_info(image.filename, len(image_data), "image processing with LLM")

        # Encode image
        image_b64 = process_uploaded_image(image_data, image.filename)

        # Get LLM analysis
        analysis = await get_response(image_b64=image_b64, prompt=prompt)

        return MultimodalResponse(
            status="success",
            message="Image processed and analyzed successfully",
            content_type="image",
            size_bytes=len(image_data),
            analysis=analysis,
        )
    except Exception as e:
        raise handle_processing_error("Image processing with LLM", e)


@router.post("/api/process-video-unified", response_model=MultimodalResponse)
async def process_video_unified(video: UploadFile = File(...), prompt: str = DEFAULT_VIDEO_PROMPT):
    """Upload video file and analyze with LLM."""
    validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)

    try:
        # Read and process video
        video_data = await video.read()
        log_upload_info(video.filename, len(video_data), "video processing with LLM")

        # Encode video with Gemini-safe processing
        video_b64, encoding_info = process_uploaded_video(video_data, video.filename)

        # Get LLM analysis
        analysis = await get_response(video_b64=video_b64, prompt=prompt)

        return MultimodalResponse(
            status="success",
            message="Video processed and analyzed successfully",
            content_type="video",
            size_bytes=len(video_data),
            analysis=analysis,
        )
    except Exception as e:
        raise handle_processing_error("Video processing with LLM", e)


@router.post("/api/process-video-base64", response_model=MultimodalResponse)
async def process_video_base64(request: VideoBase64Request):
    """Process base64 video data with LLM analysis."""
    try:
        # Decode base64 to get video data
        video_data = base64.b64decode(request.video_b64)
        log_upload_info(request.filename, len(video_data), "base64 video processing with LLM")

        # Encode video with Gemini-safe processing
        video_b64, encoding_info = process_uploaded_video(video_data, request.filename)

        # Get LLM analysis
        analysis = await get_response(video_b64=video_b64, prompt=request.prompt)

        return MultimodalResponse(
            status="success",
            message="Base64 video processed and analyzed successfully",
            content_type="video",
            size_bytes=len(video_data),
            analysis=analysis,
        )
    except Exception as e:
        raise handle_processing_error("Base64 video processing with LLM", e)


@router.post("/api/process-multimodal-unified", response_model=MultimodalResponse)
async def process_multimodal_unified(
    request: MultimodalAnalysisRequest,
    audio: UploadFile = File(None),
    image: UploadFile = File(None),
    video: UploadFile = File(None),
):
    """Process multiple media files together with LLM analysis."""
    if not any([audio, image, video]):
        raise HTTPException(status_code=400, detail="At least one media file must be provided")

    try:
        media_data = {}
        total_size = 0

        # Process audio if provided
        if audio:
            validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)
            audio_data = await audio.read()
            media_data["audio_b64"] = process_uploaded_audio(audio_data, audio.filename)
            total_size += len(audio_data)

        # Process image if provided
        if image:
            validate_file_upload(image.filename, image.content_type, IMAGE_MIME_TYPES)
            image_data = await image.read()
            media_data["image_b64"] = process_uploaded_image(image_data, image.filename)
            total_size += len(image_data)

        # Process video if provided
        if video:
            validate_file_upload(video.filename, video.content_type, VIDEO_MIME_TYPES)
            video_data = await video.read()
            video_b64, _ = process_uploaded_video(video_data, video.filename)
            media_data["video_b64"] = video_b64
            total_size += len(video_data)

        log_upload_info("multimodal", total_size, "multimodal processing with LLM")

        # Get LLM analysis with all media
        analysis = await get_response(prompt=request.prompt, **media_data)

        return MultimodalResponse(
            status="success",
            message="Multimodal content processed and analyzed successfully",
            content_type="multimodal",
            size_bytes=total_size,
            analysis=analysis,
        )
    except Exception as e:
        raise handle_processing_error("Multimodal processing with LLM", e)
