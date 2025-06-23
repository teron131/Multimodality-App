"""
Route utility functions and error handling.

Provides standardized response formatting and error handling for API endpoints.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, UploadFile

from ..media_processing import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    VIDEO_MIME_TYPES,
    process_uploaded_audio,
    process_uploaded_image,
    process_uploaded_video,
)

logger = logging.getLogger(__name__)


def success_response(message: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a standardized success response."""
    response = {"status": "success", "message": message}
    response.update(kwargs)
    return response


def error_response(message: str, error_code: Optional[str] = None, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {"status": "error", "message": message}
    if error_code:
        response["error_code"] = error_code
    if details:
        response["details"] = details
    return response


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text for logging with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def log_llm_response(operation: str, filename: str, response_content: str, size_bytes: int) -> None:
    """Log LLM response with content preview."""
    # Clean up response content for logging
    clean_content = response_content.replace("\n", " ").replace("\r", " ")
    preview = truncate_text(clean_content, 100)

    logger.info(f"✅ {operation} complete: {filename} ({size_bytes} bytes) -> {preview}")


def log_processing_start(operation: str, filename: str, size_bytes: int) -> None:
    """Log the start of processing operation."""
    logger.info(f"🔄 Starting {operation}: {filename} ({size_bytes} bytes)")


def log_multimodal_response(operation: str, content_types: list, response_content: str, total_size: int) -> None:
    """Log multimodal LLM response with content preview."""
    clean_content = response_content.replace("\n", " ").replace("\r", " ")
    preview = truncate_text(clean_content, 100)
    content_type_str = " + ".join(content_types)

    logger.info(f"✅ {operation} complete: {content_type_str} ({total_size} bytes) -> {preview}")


def handle_processing_error(operation: str, error: Exception, status_code: int = 500) -> HTTPException:
    """Standardized error handling for processing operations."""
    # Log the technical error for developers
    logger.error(f"❌ Processing error in {operation}: {error}")

    # Simplified user-friendly messages
    if "audio" in operation.lower():
        user_message = "Unable to process audio file. Please check the file format and try again."
    elif "image" in operation.lower():
        user_message = "Unable to process image file. Please check the file format and try again."
    elif "video" in operation.lower():
        user_message = "Unable to process video file. Please check the file format and try again."
    elif "multimodal" in operation.lower():
        user_message = "Unable to process files. Please check the file formats and try again."
    else:
        user_message = "Processing failed. Please try again."

    return HTTPException(status_code=status_code, detail=user_message)


def validate_file_upload(
    filename: Optional[str],
    content_type: Optional[str],
    allowed_types: set,
) -> None:
    """Validate uploaded file requirements."""
    if not filename:
        raise HTTPException(status_code=400, detail="Please select a file to upload.")

    if content_type and content_type not in allowed_types:
        logger.warning(f"⚠️ Unusual content type: {content_type}, proceeding anyway")


def log_upload_info(filename: str, size_bytes: int, operation: str = "upload") -> None:
    """Log file upload information."""
    logger.info(f"📁 Received {operation}: {filename} ({size_bytes} bytes)")


async def process_single_file(
    file: UploadFile,
    media_type: str,
    operation_name: str,
) -> Tuple[str, int]:
    """
    Unified file processing for single media files.

    Args:
        file: Uploaded file
        media_type: 'audio', 'image', or 'video'
        operation_name: Name for logging/error handling

    Returns:
        Tuple of (base64_encoded_data, file_size_bytes)
    """
    # Validate based on media type
    mime_types = {
        "audio": AUDIO_MIME_TYPES,
        "image": IMAGE_MIME_TYPES,
        "video": VIDEO_MIME_TYPES,
    }

    validate_file_upload(file.filename, file.content_type, mime_types[media_type])

    try:
        # Read file data
        file_data = await file.read()
        log_upload_info(file.filename, len(file_data), operation_name)

        # Process based on media type
        if media_type == "audio":
            encoded_data = process_uploaded_audio(file_data, file.filename)
        elif media_type == "image":
            encoded_data = process_uploaded_image(file_data, file.filename)
        elif media_type == "video":
            encoded_data, _ = process_uploaded_video(file_data, file.filename)
        else:
            raise ValueError(f"Unsupported media type: {media_type}")

        return encoded_data, len(file_data)

    except Exception as e:
        raise handle_processing_error(f"{media_type.title()} {operation_name}", e)


async def process_multimodal_files(
    audio: Optional[UploadFile] = None,
    image: Optional[UploadFile] = None,
    video: Optional[UploadFile] = None,
    operation_name: str = "multimodal processing",
) -> Dict[str, Any]:
    """
    Unified multimodal file processing.

    Returns:
        Dictionary with encoded data and metadata
    """
    if not any([audio, image, video]):
        raise HTTPException(status_code=400, detail="At least one file must be provided")

    result = {"audio_b64": None, "image_b64": None, "video_b64": None, "total_size": 0, "content_types": []}

    try:
        # Process each file type
        if audio and audio.filename:
            encoded_data, size = await process_single_file(audio, "audio", operation_name)
            result["audio_b64"] = encoded_data
            result["total_size"] += size
            result["content_types"].append("audio")

        if image and image.filename:
            encoded_data, size = await process_single_file(image, "image", operation_name)
            result["image_b64"] = encoded_data
            result["total_size"] += size
            result["content_types"].append("image")

        if video and video.filename:
            encoded_data, size = await process_single_file(video, "video", operation_name)
            result["video_b64"] = encoded_data
            result["total_size"] += size
            result["content_types"].append("video")

        log_upload_info("multimodal", result["total_size"], operation_name)
        return result

    except Exception as e:
        raise handle_processing_error(f"Multimodal {operation_name}", e)
