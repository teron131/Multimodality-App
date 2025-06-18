import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException

from ..schema import ErrorResponse, SuccessResponse

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


def handle_processing_error(operation: str, error: Exception, status_code: int = 500) -> HTTPException:
    """Standardized error handling for processing operations."""
    # Log the technical error for developers
    logger.error(f"Processing error in {operation}: {error}")

    # Provide user-friendly error messages based on operation type
    user_friendly_messages = {
        "Audio upload": "Unable to upload audio file. Please check the file format and try again.",
        "Audio processing": "Unable to process audio file. Please try again or use a different audio file.",
        "Unified audio processing": "Unable to process audio file. Please check the file format and try again.",
        "Image upload": "Unable to upload image file. Please check the file format and try again.",
        "Image processing": "Unable to process image file. Please try again or use a different image file.",
        "Unified image processing": "Unable to process image file. Please check the file format and try again.",
        "Video upload": "Unable to upload video file. Please check the file format and try again.",
        "Video processing": "Unable to process video file. Please try again or use a different video file.",
        "Unified video processing": "Unable to process video file. Please check the file format and try again.",
        "Multimodal processing": "Unable to process files. Please check the file formats and try again.",
        "Unified multimodal processing": "Unable to process files. Please check the file formats and try again.",
    }

    # Get user-friendly message or fallback to a generic one
    user_message = user_friendly_messages.get(operation, "Processing failed. Please try again.")

    return HTTPException(status_code=status_code, detail=user_message)


def validate_file_upload(filename: Optional[str], content_type: Optional[str], allowed_types: set) -> None:
    """Validate uploaded file requirements."""
    if not filename:
        raise HTTPException(status_code=400, detail="Please select a file to upload.")

    if content_type and content_type not in allowed_types:
        logger.warning(f"Unusual content type: {content_type}, proceeding anyway")


def log_upload_info(filename: str, size_bytes: int, operation: str = "upload") -> None:
    """Log file upload information."""
    logger.info(f"Received {operation}: {filename} ({size_bytes} bytes)")
