import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import APP_NAME, SERVER_HOST, SERVER_PORT, STATIC_DIR
from .routes import audio_router, image_router, main_router, multimodal_router

# Set up logging
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
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# Include route modules
app.include_router(main_router)
app.include_router(audio_router)
app.include_router(image_router)
app.include_router(multimodal_router)

logger.info(f"🚀 {APP_NAME} server initialized")


def main() -> None:
    """Main entry point for running the server."""
    import uvicorn

    logger.info(f"Starting server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run("multimodality_app.server:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)


if __name__ == "__main__":
    main()
