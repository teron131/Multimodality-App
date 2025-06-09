import logging
import logging.handlers
from pathlib import Path

from .config import DEBUG_MODE, PROJECT_ROOT

# Logs directory
LOGS_DIR = PROJECT_ROOT / "logs"


def setup_logging() -> logging.Logger:
    """Configure application-wide logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    logger.handlers.clear()

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(console)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(LOGS_DIR / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5)  # 10MB
    file_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"))
    logger.addHandler(file_handler)

    return logger


# Set up logging on import
setup_logging()
