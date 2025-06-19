"""
FastAPI server initialization and startup.

Main entry point for the multimodality app with route registration and static file serving.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import logging configuration first to set up logging
from . import logging_config  # noqa: F401
from .config import APP_NAME, SERVER_HOST, SERVER_PORT, STATIC_DIR
from .routes import llm_router, main_router, processing_router, realtime_router

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# Include route modules
app.include_router(main_router)
app.include_router(llm_router)
app.include_router(processing_router)
app.include_router(realtime_router)

logger.info(f"🚀 {APP_NAME} server initialized")


def main() -> None:
    """Main entry point for running the server."""
    import uvicorn

    logger.info(f"🚀 Starting server on http://{SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"📋 Press Ctrl+C to stop")
    logger.info(f"📁 Logs will be written to: logs/last_run.log")

    uvicorn.run("multimodality_app.server:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)


if __name__ == "__main__":
    main()
