import logging
import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .llm import get_response
from .media_processing import (
    AUDIO_MIME_TYPES,
    SUPPORTED_IMAGE_FORMATS,
    process_uploaded_audio,
    process_uploaded_image,
)

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML, CSS, JS)
static_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


# Pydantic models
class ConfigResponse(BaseModel):
    google_api_key: str
    has_key: bool
    server: str = "multimodality-app"


class StatusResponse(BaseModel):
    server_status: str = "running"
    message: str = "Audio processing ready"


class AudioUploadResponse(BaseModel):
    status: str
    message: str
    audio_base64: str
    size_bytes: int


class GeminiRequest(BaseModel):
    audio_base64: str
    api_key: Optional[str] = None
    prompt: str = "Please transcribe this audio recording and provide any additional insights about what you hear."
    max_tokens: int = 1000000


class GeminiResponse(BaseModel):
    status: str
    gemini_response: Dict


class UnifiedProcessRequest(BaseModel):
    prompt: str = "Please transcribe this audio recording and provide any additional insights about what you hear."


class UnifiedProcessResponse(BaseModel):
    status: str
    message: str
    transcription: str
    size_bytes: int


# Image processing models
class ImageUploadResponse(BaseModel):
    status: str
    message: str
    image_base64: str
    size_bytes: int


class MultimodalRequest(BaseModel):
    prompt: str = "Please analyze this content and provide insights."


class MultimodalResponse(BaseModel):
    status: str
    message: str
    analysis: str
    content_type: str
    size_bytes: int


# Routes
@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve the main HTML interface."""
    html_file = static_dir / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(html_file)


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get API configuration including Google API key status."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    return ConfigResponse(google_api_key=api_key, has_key=bool(api_key))


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get system status."""
    return StatusResponse()


@app.post("/api/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(audio: UploadFile = File(...)):
    """Upload and process audio file."""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    if audio.content_type and audio.content_type not in AUDIO_MIME_TYPES:
        logger.warning(f"Unusual content type: {audio.content_type}, proceeding anyway")

    try:
        # Read uploaded file
        audio_data = await audio.read()
        logger.info(f"Received audio upload: {audio.filename} ({len(audio_data)} bytes)")

        # Process audio (save → convert → cleanup)
        audio_base64 = process_uploaded_audio(audio_data, audio.filename)

        return AudioUploadResponse(status="success", message="Audio processed successfully", audio_base64=audio_base64, size_bytes=len(audio_data))

    except Exception as e:
        logger.error(f"Error processing audio upload: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")


@app.post("/api/process-audio", response_model=GeminiResponse)
async def process_audio(request: GeminiRequest):
    """Process audio with Gemini API (legacy endpoint - consider using /api/process-audio-unified instead)."""
    try:
        # Use enhanced LLM module instead of direct API calls
        response = get_response(text_input=request.prompt, audio_base64=request.audio_base64)

        # Convert LangChain response to legacy format for compatibility
        legacy_response = {
            "choices": [{"message": {"content": response.content}}],
            "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
        }

        return GeminiResponse(status="success", gemini_response=legacy_response)

    except Exception as e:
        logger.error(f"Error processing audio with Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/process-audio-unified", response_model=UnifiedProcessResponse)
async def process_audio_unified(audio: UploadFile = File(...), prompt: str = "Please transcribe this audio recording and provide any additional insights about what you hear."):
    """Unified endpoint: upload audio → process → get LLM response in one call."""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    if audio.content_type and audio.content_type not in AUDIO_MIME_TYPES:
        logger.warning(f"Unusual content type: {audio.content_type}, proceeding anyway")

    try:
        # Read uploaded file
        audio_data = await audio.read()
        logger.info(f"Unified processing: {audio.filename} ({len(audio_data)} bytes)")

        # Process audio (save → convert → cleanup)
        audio_base64 = process_uploaded_audio(audio_data, audio.filename)

        # Use LLM module for processing (now accepts base64 directly)
        response = get_response(text_input=prompt, audio_base64=audio_base64)

        return UnifiedProcessResponse(status="success", message="Audio processed successfully", transcription=response.content, size_bytes=len(audio_data))

    except Exception as e:
        logger.error(f"Unified processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/upload-image", response_model=ImageUploadResponse)
async def upload_image(image: UploadFile = File(...)):
    """Upload and process image file."""
    if not image.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

    try:
        # Read uploaded file
        image_data = await image.read()
        logger.info(f"Received image upload: {image.filename} ({len(image_data)} bytes)")

        # Process image (save → encode → cleanup)
        image_base64 = process_uploaded_image(image_data, image.filename)

        return ImageUploadResponse(status="success", message="Image processed successfully", image_base64=image_base64, size_bytes=len(image_data))

    except Exception as e:
        logger.error(f"Error processing image upload: {e}")
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@app.post("/api/process-image-unified", response_model=MultimodalResponse)
async def process_image_unified(image: UploadFile = File(...), prompt: str = "Please analyze this image and describe what you see."):
    """Unified endpoint: upload image → process → get LLM response in one call."""
    if not image.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type
    file_ext = Path(image.filename).suffix.lower()
    if file_ext not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

    try:
        # Read uploaded file
        image_data = await image.read()
        logger.info(f"Unified image processing: {image.filename} ({len(image_data)} bytes)")

        # Process image (save → encode → cleanup)
        image_base64 = process_uploaded_image(image_data, image.filename)

        # Use LLM module for processing with image_base64
        response = get_response(text_input=prompt, image_base64=image_base64)

        return MultimodalResponse(status="success", message="Image processed successfully", analysis=response.content, content_type="image", size_bytes=len(image_data))

    except Exception as e:
        logger.error(f"Unified image processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/api/process-multimodal-unified", response_model=MultimodalResponse)
async def process_multimodal_unified(audio: UploadFile = File(None), image: UploadFile = File(None), prompt: str = "Please analyze this content and provide insights."):
    """Unified endpoint: upload audio and/or image → process → get LLM response in one call."""
    if not audio and not image:
        raise HTTPException(status_code=400, detail="At least one file (audio or image) must be provided")

    try:
        audio_base64 = None
        image_base64 = None
        total_size = 0
        content_types = []

        # Process audio if provided
        if audio and audio.filename:
            # Validate audio file type
            if audio.content_type and audio.content_type not in AUDIO_MIME_TYPES:
                logger.warning(f"Unusual audio content type: {audio.content_type}, proceeding anyway")

            audio_data = await audio.read()
            total_size += len(audio_data)
            content_types.append("audio")

            # Process audio
            audio_base64 = process_uploaded_audio(audio_data, audio.filename)
            logger.info(f"Processed audio: {audio.filename} ({len(audio_data)} bytes)")

        # Process image if provided
        if image and image.filename:
            # Validate image file type
            file_ext = Path(image.filename).suffix.lower()
            if file_ext not in SUPPORTED_IMAGE_FORMATS:
                raise HTTPException(status_code=400, detail=f"Unsupported image format: {file_ext}. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}")

            image_data = await image.read()
            total_size += len(image_data)
            content_types.append("image")

            # Process image (save → encode → cleanup)
            image_base64 = process_uploaded_image(image_data, image.filename)
            logger.info(f"Processed image: {image.filename} ({len(image_data)} bytes)")

        # Use enhanced LLM module for multimodal processing
        response = get_response(text_input=prompt, audio_base64=audio_base64, image_base64=image_base64)

        return MultimodalResponse(status="success", message=f"Multimodal processing successful ({' + '.join(content_types)})", analysis=response.content, content_type=" + ".join(content_types), size_bytes=total_size)

    except Exception as e:
        logger.error(f"Unified multimodal processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("multimodality_app.server:app", host="127.0.0.1", port=3030, reload=True)
