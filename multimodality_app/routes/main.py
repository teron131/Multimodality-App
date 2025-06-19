"""
Main API routes for system configuration and text processing.

Provides health checks, configuration endpoints, and basic text analysis.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import GOOGLE_API_KEY, STATIC_DIR
from ..llm import get_llm_info, get_response
from ..schema import ConfigResponse, HealthResponse, StatusResponse

router = APIRouter()


class TextProcessRequest(BaseModel):
    text: str
    prompt: str = "Please analyze this text and provide insights."


@router.get("/", response_class=FileResponse)
async def serve_index():
    """Serve the main HTML interface."""
    html_file = STATIC_DIR / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(html_file)


@router.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get API configuration including backend information."""
    backend_info = get_llm_info()

    config = ConfigResponse(backend=backend_info["backend"])

    if backend_info["backend"] == "gemini":
        config.google_api_key = GOOGLE_API_KEY
        config.has_key = bool(GOOGLE_API_KEY)
    elif backend_info["backend"] == "llama":
        config.llama_host = backend_info["host"]
        config.llama_port = backend_info["port"]
        config.llama_model = backend_info["model"]

    return config


@router.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get system status."""
    backend_info = get_llm_info()
    message = f"Processing ready with {backend_info['backend']} backend"
    return StatusResponse(
        message=message,
        backend=backend_info["backend"],
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    backend_info = get_llm_info()

    if backend_info["backend"] == "llama":
        try:
            # Try to connect to llama-cuda server to verify it's running
            response = get_response(text_input="Health check")
            return HealthResponse(
                status="healthy",
                backend="llama",
                details={"llama_server": "connected", "host": backend_info["host"], "port": backend_info["port"]},
            )
        except ConnectionError:
            return HealthResponse(
                status="degraded",
                backend="llama",
                details={"llama_server": "disconnected", "message": f"llama-cuda server not available at {backend_info['host']}:{backend_info['port']}"},
            )
        except Exception as e:
            return HealthResponse(
                status="degraded",
                backend="llama",
                details={"error": str(e)},
            )
    else:
        # Gemini backend
        return HealthResponse(
            status="healthy",
            backend="gemini",
            details={"has_api_key": backend_info.get("has_api_key", False)},
        )


@router.post("/api/process-text")
async def process_text(request: TextProcessRequest):
    """Process text input directly with LLM."""
    try:
        # Combine prompt and text
        full_prompt = f"{request.prompt}\n\nText to analyze:\n{request.text}"

        # Get response from LLM
        response = get_response(text_input=full_prompt)

        return {"status": "success", "analysis": response.content, "message": "Text analysis completed"}
    except Exception as e:
        return {"status": "error", "message": f"Text processing failed: {str(e)}"}
