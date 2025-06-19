"""
Image processing and encoding for multimodal AI.

Handles image file validation and base64 encoding for LLM consumption.
"""

import base64
import logging
import tempfile
from pathlib import Path

from .utils import SUPPORTED_IMAGE_FORMATS

logger = logging.getLogger(__name__)


def encode_image(image_path: str | Path) -> str:
    """Convert image file to base64-encoded string.

    Args:
        image_path: Path to the input image file

    Returns:
        Base64-encoded image data as string

    Raises:
        ValueError: If image format is not supported
    """
    image_path = Path(image_path)
    logger.info(f"🖼️ Encoding image file: {image_path}")

    if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        error_msg = f"Unsupported image format: {image_path.suffix}. Supported formats: PNG, JPEG, WEBP, HEIC, HEIF"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        b64_data = base64.b64encode(image_data).decode("utf-8")

    logger.info(f"✅ Image encoding successful: {len(image_data)} bytes → {len(b64_data)} chars base64")
    return b64_data


def process_uploaded_image(image_data: bytes, filename: str) -> str:
    """Complete image processing workflow: save → encode → cleanup.

    Args:
        image_data: Raw image bytes from upload
        filename: Original filename to determine format

    Returns:
        Base64-encoded image data ready for Gemini API
    """
    logger.info(f"📤 Processing uploaded image: {filename} ({len(image_data)} bytes)")

    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".jpg"))
    logger.debug(f"📁 Creating temporary file: {temp_file}")

    try:
        with open(temp_file, "wb") as f:
            f.write(image_data)

        # Encode to base64
        result = encode_image(temp_file)
        logger.info(f"✅ Upload processing complete: {len(result)} chars base64")
        return result

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"🗑️ Cleaned up temporary file: {temp_file}")
