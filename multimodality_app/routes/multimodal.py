from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import DEFAULT_MULTIMODAL_PROMPT
from ..llm import get_response
from ..media_processing import (
    AUDIO_MIME_TYPES,
    SUPPORTED_IMAGE_FORMATS,
    process_uploaded_audio,
    process_uploaded_image,
)
from ..schema import MultimodalResponse
from .utils import handle_processing_error, log_upload_info, validate_file_upload

router = APIRouter()


@router.post("/api/process-multimodal-unified", response_model=MultimodalResponse)
async def process_multimodal_unified(audio: UploadFile = File(None), image: UploadFile = File(None), prompt: str = DEFAULT_MULTIMODAL_PROMPT):
    """Unified endpoint: upload audio and/or image → process → get LLM response in one call."""
    if not audio and not image:
        raise HTTPException(status_code=400, detail="At least one file (audio or image) must be provided")

    try:
        audio_base64 = None
        image_base64 = None
        total_size = 0
        content_types = []

        # Process audio if provided
        if audio and audio.filename:
            validate_file_upload(audio.filename, audio.content_type, AUDIO_MIME_TYPES)

            audio_data = await audio.read()
            total_size += len(audio_data)
            content_types.append("audio")

            # Process audio
            audio_base64 = process_uploaded_audio(audio_data, audio.filename)
            log_upload_info(audio.filename, len(audio_data), "multimodal audio")

        # Process image if provided
        if image and image.filename:
            # Validate image file type
            file_ext = Path(image.filename).suffix.lower()
            if file_ext not in SUPPORTED_IMAGE_FORMATS:
                raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

            image_data = await image.read()
            total_size += len(image_data)
            content_types.append("image")

            # Process image
            image_base64 = process_uploaded_image(image_data, image.filename)
            log_upload_info(image.filename, len(image_data), "multimodal image")

        # Use enhanced LLM module for multimodal processing
        response = get_response(text_input=prompt, audio_base64=audio_base64, image_base64=image_base64)

        content_type_str = " + ".join(content_types)

        return MultimodalResponse(status="success", message=f"Multimodal processing successful ({content_type_str})", analysis=response.content, content_type=content_type_str, size_bytes=total_size)

    except Exception as e:
        raise handle_processing_error("Unified multimodal processing", e)
