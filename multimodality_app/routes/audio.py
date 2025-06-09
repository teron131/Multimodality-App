from fastapi import APIRouter, File, UploadFile

from ..config import DEFAULT_AUDIO_PROMPT
from ..llm import get_response
from ..media_processing import AUDIO_MIME_TYPES, process_uploaded_audio
from ..schema import (
    AudioUploadResponse,
    GeminiRequest,
    GeminiResponse,
    UnifiedProcessResponse,
)
from .utils import handle_processing_error, log_upload_info, validate_file_upload

router = APIRouter()


@router.post("/api/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(audio: UploadFile = File(...)):
    """Upload and process audio file."""
    validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

    try:
        # Read uploaded file
        audio_data = await audio.read()
        log_upload_info(audio.filename, len(audio_data), "audio upload")

        # Process audio (save → convert → cleanup)
        audio_base64 = process_uploaded_audio(audio_data, audio.filename)

        return AudioUploadResponse(
            status="success",
            message="Audio processed successfully",
            audio_base64=audio_base64,
            size_bytes=len(audio_data),
        )

    except Exception as e:
        raise handle_processing_error("Audio upload", e)


@router.post("/api/process-audio", response_model=GeminiResponse)
async def process_audio(request: GeminiRequest):
    """Process audio with LLM (legacy endpoint - consider using /api/process-audio-unified)."""
    try:
        # Use enhanced LLM module instead of direct API calls
        response = get_response(text_input=request.prompt, audio_base64=request.audio_base64)

        # Convert LangChain response to legacy format for compatibility
        legacy_response = {
            "choices": [{"message": {"content": response.content}}],
            "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
        }

        return GeminiResponse(status="success", gemini_response=legacy_response)

    except Exception as e:
        raise handle_processing_error("Audio processing", e)


@router.post("/api/process-audio-unified", response_model=UnifiedProcessResponse)
async def process_audio_unified(audio: UploadFile = File(...), prompt: str = DEFAULT_AUDIO_PROMPT):
    """Unified endpoint: upload audio → process → get LLM response in one call."""
    validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

    try:
        # Read uploaded file
        audio_data = await audio.read()
        log_upload_info(audio.filename, len(audio_data), "unified audio processing")

        # Process audio (save → convert → cleanup)
        audio_base64 = process_uploaded_audio(audio_data, audio.filename)

        # Use LLM module for processing (now accepts base64 directly)
        response = get_response(text_input=prompt, audio_base64=audio_base64)

        return UnifiedProcessResponse(
            status="success",
            message="Audio processed successfully",
            transcription=response.content,
            size_bytes=len(audio_data),
        )

    except Exception as e:
        raise handle_processing_error("Unified audio processing", e)
