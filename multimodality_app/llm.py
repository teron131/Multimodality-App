"""
LLM integration with support for multiple backends (Gemini, Llama).

Provides unified interface for multimodal AI processing with automatic backend switching.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .media_processing import encode_audio, encode_image, encode_video

logger = logging.getLogger(__name__)

load_dotenv()

# Configuration - determine which LLM backend to use
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini").lower()  # "gemini" or "llama"
BACKEND_PORT = os.getenv("BACKEND_PORT", "8080")

# Initialize LLM based on backend configuration
logger.info(f"🔧 Initializing LLM backend: {LLM_BACKEND}")

if LLM_BACKEND == "gemini":
    model_name = os.getenv("GEMINI_MODEL")
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        logger.error("❌ GOOGLE_API_KEY not found in environment variables")
        raise ValueError("GOOGLE_API_KEY is required for Gemini backend")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    logger.info(f"♊ Gemini backend initialized: {model_name}")

elif LLM_BACKEND == "llama":
    model_name = os.getenv("LLAMA_MODEL")
    base_url = f"http://localhost:{BACKEND_PORT}/v1"

    llm = ChatOpenAI(
        model=model_name,
        base_url=base_url,
    )
    logger.info(f"🦙 Llama backend initialized: {model_name} at {base_url}")

else:
    error_msg = f"Unknown LLM backend: {LLM_BACKEND}. Supported: 'gemini', 'llama'"
    logger.error(f"❌ {error_msg}")
    raise ValueError(error_msg)


def get_response(
    text_input: str = None,
    image_paths: list[str | Path] = None,
    image_b64s: list[str] = None,
    audio_paths: list[str | Path] = None,
    audio_b64s: list[str] = None,
    video_paths: list[str | Path] = None,
    video_b64s: list[str] = None,
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

    logger.info(f"🤖 LLM request: {', '.join(inputs_summary)} → {LLM_BACKEND}")

    # Validate inputs
    all_inputs = [text_input, image_paths, image_b64s, audio_paths, audio_b64s, video_paths, video_b64s]

    if not any(all_inputs):
        logger.error("❌ No inputs provided to LLM")
        raise ValueError("At least one input must be provided")

    # Build content array
    content = []

    # Handle image inputs
    if image_paths or image_b64s:
        logger.debug(f"🖼️ Processing images: paths={len(image_paths or [])}, b64s={len(image_b64s or [])}")
        image_data = image_b64s or [encode_image(path) for path in (image_paths or [])]
        for i, image_b64 in enumerate(image_data):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                }
            )
            logger.debug(f"🖼️ Added image {i+1}: {len(image_b64)} chars")

    # Handle audio inputs
    if audio_paths or audio_b64s:
        logger.debug(f"🎵 Processing audio: paths={len(audio_paths or [])}, b64s={len(audio_b64s or [])}")
        audio_data = audio_b64s or [encode_audio(path) for path in (audio_paths or [])]
        for i, audio_b64 in enumerate(audio_data):
            content.append(
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_b64,
                        "format": "mp3",
                    },
                }
            )
            logger.debug(f"🎵 Added audio {i+1}: {len(audio_b64)} chars")

    # Handle video inputs
    if video_paths or video_b64s:
        logger.debug(f"🎬 Processing videos: paths={len(video_paths or [])}, b64s={len(video_b64s or [])}")
        video_data = video_b64s or [encode_video(path) for path in (video_paths or [])]
        for i, video_b64 in enumerate(video_data):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:video/mp4;base64,{video_b64}",
                    },
                }
            )
            logger.debug(f"🎬 Added video {i+1}: {len(video_b64)} chars")

    # If combining text and image/audio/video, place the text prompt after
    if text_input:
        content.append({"type": "text", "text": text_input})
        logger.debug(f"📝 Added text input: {len(text_input)} chars")

    logger.info(f"🚀 Sending {len(content)} content items to {LLM_BACKEND}")

    try:
        response = llm.invoke([HumanMessage(content=content)])
        logger.info(f"✅ LLM response received: {len(response.content)} chars")
        return response
    except Exception as e:
        logger.error(f"❌ LLM request failed: {e}", exc_info=True)
        raise


def get_llm_info() -> dict:
    """Get information about the current LLM backend configuration.

    Returns:
        Dictionary containing backend configuration details.
    """
    logger.debug(f"🔍 Getting LLM info for backend: {LLM_BACKEND}")

    if LLM_BACKEND == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        has_api_key = bool(os.getenv("GOOGLE_API_KEY"))

        info = {
            "backend": "gemini",
            "model": model,
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "local": False,
            "api_key_required": True,
            "has_api_key": has_api_key,
        }

        logger.debug(f"♊ Gemini info: model={model}, has_key={has_api_key}")
        return info

    elif LLM_BACKEND == "llama":
        model = os.getenv("LLAMA_MODEL", "llama3.2")
        url = f"http://localhost:{BACKEND_PORT}/v1"

        info = {
            "backend": "llama",
            "host": "localhost",
            "port": BACKEND_PORT,
            "model": model,
            "url": url,
            "local": True,
            "api_key_required": False,
        }

        logger.debug(f"🦙 Llama info: model={model}, url={url}")
        return info

    else:
        logger.error(f"❌ Unknown backend in get_llm_info: {LLM_BACKEND}")
        return {"error": f"Unknown backend: {LLM_BACKEND}"}
