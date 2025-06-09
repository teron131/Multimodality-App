import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .media_processing import encode_audio, encode_image

load_dotenv()

# Configuration - determine which LLM backend to use
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini").lower()  # "gemini" or "llama"
BACKEND_PORT = os.getenv("BACKEND_PORT", "8081")

# Initialize LLM based on backend configuration
if LLM_BACKEND == "gemini":
    llm = ChatOpenAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20"),
        api_key=os.getenv("GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    print(f"♊ Using Gemini backend: {os.getenv('GEMINI_MODEL', 'default')}")

elif LLM_BACKEND == "llama":
    llm = ChatOpenAI(
        model=os.getenv("LLAMA_MODEL", "ultravox-v0_5-llama-3_2-1b"),
        base_url=f"http://localhost:{BACKEND_PORT}/v1",
    )
    print(f"🦙 Using Llama backend: localhost:{BACKEND_PORT}")


def get_response(
    text_input: str = None,
    image_path: str | Path = None,
    image_base64: str = None,
    audio_path: str | Path = None,
    audio_base64: str = None,
) -> AIMessage:
    """Get a response from the configured LLM backend. At least one input must be provided.

    Args:
        text_input: The text input to the LLM.
        image_path: The path to the image to be sent to the LLM.
        image_base64: Pre-encoded image data (alternative to image_path).
        audio_path: The path to the audio to be sent to the LLM.
        audio_base64: Pre-encoded audio data (alternative to audio_path).

    Returns:
        The response from the LLM.
    """
    # Validate inputs
    all_inputs = [text_input, image_path, image_base64, audio_path, audio_base64]
    if not any(all_inputs):
        raise ValueError("At least one input must be provided")

    if image_path and image_base64:
        raise ValueError("Only one of image_path or image_base64 must be provided")
    if audio_path and audio_base64:
        raise ValueError("Only one of audio_path or audio_base64 must be provided")

    # Build content array
    content = []

    if text_input:
        content.append({"type": "text", "text": text_input})

    # Handle image inputs
    if image_path:
        image_data = encode_image(image_path)
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}})
    elif image_base64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}})

    # Handle audio inputs
    if audio_path:
        audio_data = encode_audio(audio_path)
        content.append({"type": "input_audio", "input_audio": {"data": audio_data, "format": "mp3"}})
    elif audio_base64:
        content.append({"type": "input_audio", "input_audio": {"data": audio_base64, "format": "mp3"}})

    response = llm.invoke([HumanMessage(content=content)])
    return response


def get_llm_info() -> dict:
    """Get information about the current LLM backend configuration.

    Returns:
        Dictionary containing backend configuration details.
    """
    if LLM_BACKEND == "gemini":
        return {
            "backend": "gemini",
            "model": os.getenv("GEMINI_MODEL", "unknown"),
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "local": False,
            "api_key_required": True,
            "has_api_key": bool(os.getenv("GOOGLE_API_KEY")),
        }
    elif LLM_BACKEND == "llama":
        return {
            "backend": "llama",
            "host": "localhost",
            "port": BACKEND_PORT,
            "model": os.getenv("LLAMA_MODEL", "unknown"),
            "url": f"http://localhost:{BACKEND_PORT}/v1",
            "local": True,
            "api_key_required": False,
        }
