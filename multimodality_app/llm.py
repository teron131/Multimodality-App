import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .media_processing import encode_audio, encode_image, encode_video

load_dotenv()

# Configuration - determine which LLM backend to use
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini").lower()  # "gemini" or "llama"
BACKEND_PORT = os.getenv("BACKEND_PORT", "8080")

# Initialize LLM based on backend configuration
if LLM_BACKEND == "gemini":
    llm = ChatOpenAI(
        model=os.getenv("GEMINI_MODEL"),
        api_key=os.getenv("GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    print(f"♊ Using Gemini backend: {os.getenv('GEMINI_MODEL', 'default')}")

elif LLM_BACKEND == "llama":
    llm = ChatOpenAI(
        model=os.getenv("LLAMA_MODEL"),
        base_url=f"http://localhost:{BACKEND_PORT}/v1",
    )
    print(f"🦙 Using Llama backend: localhost:{BACKEND_PORT}")


def get_response(
    text_input: str = None,
    image_paths: list[str | Path] = None,
    image_base64s: list[str] = None,
    audio_paths: list[str | Path] = None,
    audio_base64s: list[str] = None,
    video_paths: list[str | Path] = None,
    video_base64s: list[str] = None,
) -> AIMessage:
    """Get a response from the configured LLM backend. At least one input must be provided.

    Args:
        text_input: The text input to the LLM.
        image_paths: The paths to the images to be sent to the LLM.
        image_base64s: Pre-encoded image data (alternative to image_paths).
        audio_paths: The paths to the audio to be sent to the LLM.
        audio_base64s: Pre-encoded audio data (alternative to audio_paths).
        video_paths: The paths to the video to be sent to the LLM.
        video_base64s: Pre-encoded video data (alternative to video_paths).

    Returns:
        The response from the LLM.
    """
    # Validate inputs
    all_inputs = [text_input, image_paths, image_base64s, audio_paths, audio_base64s, video_paths, video_base64s]

    if not any(all_inputs):
        raise ValueError("At least one input must be provided")

    # Build content array
    content = []
    # Handle image inputs
    image_data = image_base64s or [encode_image(path) for path in (image_paths or [])]
    for image_base64 in image_data:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            }
        )

    # Handle audio inputs
    audio_data = audio_base64s or [encode_audio(path) for path in (audio_paths or [])]
    for audio_base64 in audio_data:
        content.append(
            {
                "type": "input_audio",
                "input_audio": {
                    "data": audio_base64,
                    "format": "mp3",
                },
            }
        )

    # Handle video inputs
    video_data = video_base64s or [encode_video(path) for path in (video_paths or [])]
    for video_base64 in video_data:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:video/mp4;base64,{video_base64}",
                },
            }
        )

    # If combining text and image/audio/video, place the text prompt after
    if text_input:
        content.append({"type": "text", "text": text_input})

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
            "model": os.getenv("GEMINI_MODEL"),
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
            "model": os.getenv("LLAMA_MODEL"),
            "url": f"http://localhost:{BACKEND_PORT}/v1",
            "local": True,
            "api_key_required": False,
        }
