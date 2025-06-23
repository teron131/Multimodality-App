"""
Pydantic models for API request and response schemas.

Defines data structures for all API endpoints with validation and serialization.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# BASE MODELS
# =============================================================================


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


# =============================================================================
# SYSTEM MODELS
# =============================================================================


class System:
    """System-related response models."""

    class Config(BaseModel):
        backend: str
        google_api_key: str = ""
        has_key: bool = False
        llama_host: str = ""
        llama_port: str = ""
        llama_model: str = ""
        server: str = "multimodality-app"

    class Status(BaseModel):
        server_status: str = "running"
        message: str = "Processing ready"
        backend: str

    class Health(BaseModel):
        status: str
        backend: str
        details: Optional[Dict] = None


# =============================================================================
# MEDIA PROCESSING MODELS
# =============================================================================


class Media:
    """Media processing models - file encoding and metadata extraction."""

    class AudioRequest(BaseModel):
        """Audio processing request."""

        filename: str
        size_mb: float = Field(ge=0)

    class ImageRequest(BaseModel):
        """Image processing request."""

        filename: str
        size_mb: float = Field(ge=0)

    class VideoRequest(BaseModel):
        """Video processing request."""

        filename: str
        size_mb: float = Field(ge=0)

    # Response Models
    class Base(SuccessResponse):
        """Base media response with common fields."""

        size_bytes: int

    class Audio(Base):
        """Audio processing response."""

        audio_b64: str
        audio_info: dict
        size_bytes: int

    class Image(Base):
        """Image processing response."""

        image_b64: str
        image_info: dict
        size_bytes: int

    class Video(Base):
        """Video processing response."""

        video_b64: str
        video_info: dict
        size_bytes: int

    class Multimodal(Base):
        audio_b64: Optional[str] = None
        image_b64: Optional[str] = None
        video_b64: Optional[str] = None
        total_size_bytes: int
        content_types: List[str]

    class VideoInfo(Base):
        """Video information extraction response."""

        video_info: Dict


# =============================================================================
# LLM PROCESSING MODELS
# =============================================================================


class LLM:
    """LLM processing request and response models."""

    # Request Models
    class Request:
        class Base(BaseModel):
            """Base processing request model."""

            prompt: str = Field(default="Please analyze this content and provide insights.")
            conversation_mode: bool = Field(default=False, description="Enable conversation mode for brief responses")

        class Text(Base):
            text: str

        class VideoBase64(Base):
            """Video analysis request with base64 data."""

            video_b64: str
            filename: str

    # Response Models
    class Response:
        class Base(SuccessResponse):
            """Base LLM response with content analysis."""

            content_type: str
            size_bytes: int

        class Text(Base):
            analysis: str

        class Audio(SuccessResponse):
            """Audio processing with transcription and analysis."""

            transcription: str  # Contains transcription and additional insights
            size_bytes: int

        class Image(Base):
            analysis: str

        class Video(Base):
            analysis: str

        class Multimodal(Base):
            analysis: str


# =============================================================================
# REALTIME MODELS
# =============================================================================


class Realtime:
    """Real-time WebSocket API models."""

    class Config(BaseModel):
        modalities: List[str] = Field(default=["text"])
        instructions: Optional[str] = None
        voice: Optional[str] = Field(default="alloy")
        input_audio_format: str = Field(default="pcm16")
        output_audio_format: str = Field(default="pcm16")
        temperature: float = Field(default=0.6)

    class Session(BaseModel):
        event_id: str
        type: str
        session: Realtime.Config

    class Item(BaseModel):
        id: str
        object: str = "realtime.item"
        type: str
        role: str
        content: List[Dict]

    class Response(BaseModel):
        id: str
        object: str = "realtime.response"
        status: str
        output: List[Realtime.Item]
