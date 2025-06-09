from typing import Dict, Optional

from pydantic import BaseModel, Field


# Standard Response Models
class BaseResponse(BaseModel):
    """Base response model with standard fields."""

    status: str
    message: str


class ErrorResponse(BaseResponse):
    """Standard error response format."""

    status: str = "error"
    error_code: Optional[str] = None
    details: Optional[Dict] = None


class SuccessResponse(BaseResponse):
    """Standard success response format."""

    status: str = "success"


# Configuration Models
class ConfigResponse(BaseModel):
    backend: str
    google_api_key: str = ""
    has_key: bool = False
    llama_host: str = ""
    llama_port: str = ""
    llama_model: str = ""
    server: str = "multimodality-app"


class StatusResponse(BaseModel):
    server_status: str = "running"
    message: str = "Processing ready"
    backend: str


class HealthResponse(BaseModel):
    status: str
    backend: str
    details: Optional[Dict] = None


# Upload Response Models
class UploadResponse(SuccessResponse):
    """Base upload response with common fields."""

    size_bytes: int


class AudioUploadResponse(UploadResponse):
    audio_base64: str


class ImageUploadResponse(UploadResponse):
    image_base64: str


# Processing Request Models
class ProcessingRequest(BaseModel):
    """Base processing request model."""

    prompt: str = Field(default="Please analyze this content and provide insights.")


class GeminiRequest(BaseModel):
    """Legacy Gemini API request format."""

    audio_base64: str
    api_key: Optional[str] = None
    prompt: str = "Please transcribe this audio recording and provide any additional insights about what you hear."
    max_tokens: int = 1000000


class MultimodalRequest(ProcessingRequest):
    """Request for multimodal content processing."""

    pass


# Processing Response Models
class ProcessingResponse(SuccessResponse):
    """Base processing response with content analysis."""

    content_type: str
    size_bytes: int


class GeminiResponse(BaseModel):
    """Legacy Gemini API response format."""

    status: str
    gemini_response: Dict


class UnifiedProcessResponse(SuccessResponse):
    """Unified audio processing response."""

    transcription: str
    size_bytes: int


class MultimodalResponse(ProcessingResponse):
    """Multimodal content analysis response."""

    analysis: str
