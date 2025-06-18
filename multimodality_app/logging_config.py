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

    # Console handler with improved formatting
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(console)

    # Last run file handler (overwrites each time)
    last_run_handler = logging.FileHandler(LOGS_DIR / "last_run.log", mode="w")  # Overwrite mode
    last_run_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    last_run_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"))
    logger.addHandler(last_run_handler)

    return logger


# Set up logging on import
setup_logging()
