"""
LLM integration using the Google GenAI SDK for Gemini models.

Provides a unified interface for multimodal AI processing.
"""

import base64
import logging
from pathlib import Path
from typing import List, Optional, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .config import CONVERSATION_TEXT_SUFFIX, GEMINI_API_KEY, GEMINI_MODEL
from .media_processing.audio import encode_audio
from .media_processing.image import encode_image
from .media_processing.video import encode_video

logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Google GenAI client
api_key = GEMINI_API_KEY
if not api_key:
    logger.error("❌ GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY is required for the Gemini backend")

client = genai.Client(api_key=api_key)
logger.info(f"♊ Gemini backend initialized: {GEMINI_MODEL}")


class AIMessage:
    """Simple wrapper to maintain compatibility with existing code."""

    def __init__(self, content: str):
        self.content = content


def _create_content_parts(
    text_input: Optional[str] = None,
    image_b64s: Optional[List[str]] = None,
    audio_b64s: Optional[List[str]] = None,
    video_b64s: Optional[List[str]] = None,
) -> List[Union[str, types.Part]]:
    """Create content parts for Gemini API.

    Args:
        text_input: Text content
        image_b64s: Base64 encoded images
        audio_b64s: Base64 encoded audio files
        video_b64s: Base64 encoded videos

    Returns:
        List of content parts for Gemini API
    """
    parts = []

    # Add images
    if image_b64s:
        for image_b64 in image_b64s:
            parts.append(types.Part.from_bytes(data=base64.b64decode(image_b64), mime_type="image/png"))

    # Add audio
    if audio_b64s:
        for audio_b64 in audio_b64s:
            parts.append(types.Part.from_bytes(data=base64.b64decode(audio_b64), mime_type="audio/mp3"))

    # Add videos
    if video_b64s:
        for video_b64 in video_b64s:
            parts.append(types.Part.from_bytes(data=base64.b64decode(video_b64), mime_type="video/mp4"))

    # Add text last for better context
    if text_input:
        parts.append(text_input)

    return parts


def get_response(
    text_input: str = None,
    image_paths: list[str | Path] = None,
    image_b64s: list[str] = None,
    audio_paths: list[str | Path] = None,
    audio_b64s: list[str] = None,
    video_paths: list[str | Path] = None,
    video_b64s: list[str] = None,
    conversation_mode: bool = False,
) -> AIMessage:
    """Get a response from the configured LLM backend. At least one input must be provided.

    Args:
        text_input: The text input to the LLM.
        image_paths: The paths to the images to be sent to the LLM.
        image_b64s: Pre-encoded image data (alternative to image_paths).
        audio_paths: The paths to the audio to be sent to the LLM.
        audio_b64s: Pre-encoded audio data (alternative to audio_paths).
        video_paths: The paths to the video to be sent to the LLM.
        video_b64s: Pre-encoded video data (alternative to video_paths).
        conversation_mode: Enable conversation mode for brief, focused responses.

    Returns:
        The response from the LLM.
    """
    # Log the request details
    inputs_summary = []
    if text_input:
        inputs_summary.append(f"text({len(text_input)} chars)")
    if image_paths:
        inputs_summary.append(f"image_paths({len(image_paths)})")
    if image_b64s:
        inputs_summary.append(f"image_b64s({len(image_b64s)})")
    if audio_paths:
        inputs_summary.append(f"audio_paths({len(audio_paths)})")
    if audio_b64s:
        inputs_summary.append(f"audio_b64s({len(audio_b64s)})")
    if video_paths:
        inputs_summary.append(f"video_paths({len(video_paths)})")
    if video_b64s:
        inputs_summary.append(f"video_b64s({len(video_b64s)})")

    logger.info(f"🤖 LLM request: {', '.join(inputs_summary)} → Gemini")

    # Validate inputs
    all_inputs = [text_input, image_paths, image_b64s, audio_paths, audio_b64s, video_paths, video_b64s]

    if not any(all_inputs):
        logger.error("❌ No inputs provided to LLM")
        raise ValueError("At least one input must be provided")

    # Process file paths to base64 if needed
    if image_paths:
        image_b64s = (image_b64s or []) + [encode_image(path) for path in image_paths]
    if audio_paths:
        audio_b64s = (audio_b64s or []) + [encode_audio(path) for path in audio_paths]
    if video_paths:
        video_b64s = (video_b64s or []) + [encode_video(path) for path in video_paths]

    # Modify text for conversation mode
    if conversation_mode and text_input:
        text_input = text_input + CONVERSATION_TEXT_SUFFIX
        logger.debug(f"💬 Conversation mode enabled - modified prompt")

    # Create content parts for Gemini
    content_parts = _create_content_parts(text_input=text_input, image_b64s=image_b64s, audio_b64s=audio_b64s, video_b64s=video_b64s)

    logger.info(f"🚀 Sending {len(content_parts)} content parts to Gemini")

    try:
        # Configure generation parameters
        config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=8192 if not conversation_mode else 150,
        )

        # Generate response using Gemini
        response = client.models.generate_content(model=GEMINI_MODEL, contents=content_parts, config=config)

        # Extract text from response
        response_text = response.text if hasattr(response, "text") else str(response)

        logger.info(f"✅ LLM response received: {len(response_text)} chars")
        if conversation_mode and response_text:
            logger.debug(f"💬 Conversation response content: {response_text[:200]}...")

        # Final check for empty response
        if not response_text:
            logger.error("❌ LLM returned empty response")
            response_text = "I apologize, but I couldn't generate a response. Please try again."

        return AIMessage(content=response_text)

    except Exception as e:
        logger.error(f"❌ LLM request failed: {e}", exc_info=True)
        raise


def get_llm_info() -> dict:
    """Get information about the current LLM backend configuration.

    Returns:
        Dictionary containing backend configuration details.
    """
    logger.debug("🔍 Getting LLM info for Gemini backend")

    has_api_key = bool(GEMINI_API_KEY)

    info = {
        "backend": "gemini",
        "model": GEMINI_MODEL,
        "url": "https://generativelanguage.googleapis.com/v1beta/",
        "local": False,
        "api_key_required": True,
        "has_api_key": has_api_key,
        "sdk": "google-genai",
    }

    logger.debug(f"♊ Gemini info: model={GEMINI_MODEL}, has_key={has_api_key}")
    return info
