import base64
import tempfile
from pathlib import Path

from .utils import SUPPORTED_IMAGE_FORMATS


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

    if image_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(f"Unsupported image format: {image_path.suffix}. Supported formats: PNG, JPEG, WEBP, HEIC, HEIF")

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def process_uploaded_image(image_data: bytes, filename: str) -> str:
    """Complete image processing workflow: save → encode → cleanup.

    Args:
        image_data: Raw image bytes from upload
        filename: Original filename to determine format

    Returns:
        Base64-encoded image data ready for Gemini API
    """
    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix=Path(filename).suffix or ".jpg"))

    try:
        with open(temp_file, "wb") as f:
            f.write(image_data)

        # Encode to base64
        return encode_image(temp_file)

    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
