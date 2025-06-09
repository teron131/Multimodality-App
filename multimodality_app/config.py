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

# LLM Backend Configuration
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8080")

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
AUDIO_DIR = PROJECT_ROOT / "audio"
IMAGE_DIR = PROJECT_ROOT / "image"
STATIC_DIR = Path(__file__).parent

# Processing Configuration
DEFAULT_AUDIO_PROMPT = "Please transcribe this audio recording and provide any additional insights about what you hear."
DEFAULT_IMAGE_PROMPT = "Please analyze this image and describe what you see."
DEFAULT_MULTIMODAL_PROMPT = "Please analyze this content and provide insights."
DEFAULT_MAX_TOKENS = 1000000


def validate_config() -> None:
    """Validate configuration and create required directories."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


# Validate configuration on import
validate_config()
