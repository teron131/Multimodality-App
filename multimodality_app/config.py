"""
Configuration management for the multimodality app.

Centralized configuration with environment variables, paths, and processing defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Application Configuration
APP_NAME = "multimodality-app"
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "3030"))

# Gemini Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
AUDIO_DIR = PROJECT_ROOT / "audio"
IMAGE_DIR = PROJECT_ROOT / "image"
STATIC_DIR = Path(__file__).parent / "static"

# Processing Configuration
DEFAULT_AUDIO_PROMPT = "Please transcribe this audio recording and provide any additional insights about what you hear."
DEFAULT_IMAGE_PROMPT = "Please analyze this image and describe what you see."
DEFAULT_VIDEO_PROMPT = "Please analyze this video and describe what you see, including any actions, scenes, or notable details."
DEFAULT_MULTIMODAL_PROMPT = "Please analyze this content and provide insights."
DEFAULT_MAX_TOKENS = 1000000

# Conversation Mode Configuration
CONVERSATION_MAX_TOKENS = 500
CONVERSATION_AUDIO_PROMPT = "In one brief sentence (under 15 words), transcribe the main content."
CONVERSATION_IMAGE_PROMPT = "In one brief sentence (under 15 words), describe what you see."
CONVERSATION_VIDEO_PROMPT = "In one brief sentence (under 15 words), describe the main action."
CONVERSATION_MULTIMODAL_PROMPT = "In one brief sentence (under 15 words), summarize the content."
CONVERSATION_TEXT_SUFFIX = "\n\nIMPORTANT: Respond in ONE brief sentence only (maximum 15 words)."


def validate_config() -> None:
    """Validate configuration and create required directories."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


# Validate configuration on import
validate_config()
