from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import DEFAULT_IMAGE_PROMPT
from ..llm import get_response
from ..media_processing import SUPPORTED_IMAGE_FORMATS, process_uploaded_image
from ..schema import ImageUploadResponse, MultimodalResponse
from .utils import handle_processing_error, log_upload_info

router = APIRouter()


@router.post("/api/upload-image", response_model=ImageUploadResponse)
async def upload_image(image: UploadFile = File(...)):
    """Upload and process image file."""
    if not image.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

    try:
        # Read uploaded file
        image_data = await image.read()
        log_upload_info(image.filename, len(image_data), "image upload")

        # Process image (save → encode → cleanup)
        image_base64 = process_uploaded_image(image_data, image.filename)

        return ImageUploadResponse(status="success", message="Image processed successfully", image_base64=image_base64, size_bytes=len(image_data))

    except Exception as e:
        raise handle_processing_error("Image upload", e)


@router.post("/api/process-image-unified", response_model=MultimodalResponse)
async def process_image_unified(image: UploadFile = File(...), prompt: str = DEFAULT_IMAGE_PROMPT):
    """Unified endpoint: upload image → process → get LLM response in one call."""
    if not image.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

    try:
        # Read uploaded file
        image_data = await image.read()
        log_upload_info(image.filename, len(image_data), "unified image processing")

        # Process image (save → encode → cleanup)
        image_base64 = process_uploaded_image(image_data, image.filename)

        # Use LLM module for processing with image_base64
        response = get_response(text_input=prompt, image_base64=image_base64)

        return MultimodalResponse(
            status="success",
            message="Image processed successfully",
            analysis=response.content,
            content_type="image",
            size_bytes=len(image_data),
        )

    except Exception as e:
        raise handle_processing_error("Unified image processing", e)
