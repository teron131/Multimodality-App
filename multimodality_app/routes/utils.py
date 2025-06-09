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
    error_msg = f"{operation} failed: {str(error)}"
    logger.error(f"Processing error in {operation}: {error}")
    return HTTPException(status_code=status_code, detail=error_msg)


def validate_file_upload(filename: Optional[str], content_type: Optional[str], allowed_types: set) -> None:
    """Validate uploaded file requirements."""
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if content_type and content_type not in allowed_types:
        logger.warning(f"Unusual content type: {content_type}, proceeding anyway")


def log_upload_info(filename: str, size_bytes: int, operation: str = "upload") -> None:
    """Log file upload information."""
    logger.info(f"Received {operation}: {filename} ({size_bytes} bytes)")
