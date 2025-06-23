"""
Main API routes for system configuration and health checks.

Provides health checks, configuration endpoints, and static file serving.
LLM inference is handled in llm.py routes.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..config import GOOGLE_API_KEY, STATIC_DIR
from ..llm import get_llm_info
from ..schema import System

router = APIRouter()


@router.get("/", response_class=FileResponse)
async def get_index():
    """Serve the main index page."""
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/api/health", response_model=System.Health)
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        llm_info = get_llm_info()
        return System.Health(
            status="healthy",
            backend=llm_info["backend"],
            details=llm_info,
        )
    except Exception as e:
        return System.Health(
            status="unhealthy",
            backend="unknown",
            details={"error": str(e)},
        )


@router.get("/api/status", response_model=System.Status)
async def get_status():
    """Get server status and backend information."""
    try:
        llm_info = get_llm_info()
        return System.Status(
            server_status="running",
            message="Processing ready",
            backend=llm_info["backend"],
        )
    except Exception as e:
        return System.Status(
            server_status="error",
            message=f"Backend connection failed: {str(e)}",
            backend="unknown",
        )


@router.get("/api/config", response_model=System.Config)
async def get_config():
    """Get configuration information."""
    try:
        llm_info = get_llm_info()
        return System.Config(
            backend=llm_info["backend"],
            google_api_key="Loaded" if GOOGLE_API_KEY else "Not loaded",
            has_key=bool(GOOGLE_API_KEY),
            llama_host=llm_info.get("host", ""),
            llama_port=llm_info.get("port", ""),
            llama_model=llm_info.get("model", ""),
            server="multimodality-app",
        )
    except Exception as e:
        return System.Config(
            backend="unknown",
            google_api_key="",
            has_key=False,
            llama_host="",
            llama_port="",
            llama_model="",
            server="multimodality-app",
        )
