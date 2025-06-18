import json
import logging
import logging.handlers
import re
from pathlib import Path

from .config import DEBUG_MODE, PROJECT_ROOT

# Logs directory
LOGS_DIR = PROJECT_ROOT / "logs"


class MediaDataFilter(logging.Filter):
    """Filter to prevent logging of binary/raw media data while preserving metadata."""

    # Media-specific keys that commonly contain binary data
    BINARY_DATA_KEYS = {"audio", "image", "video", "file", "data", "content", "base64", "binary", "bytes", "buffer", "blob"}

    def filter(self, record):
        """Filter log records to sanitize binary data."""
        try:
            # Sanitize the main message
            if hasattr(record, "msg") and record.msg:
                record.msg = self._sanitize_string(str(record.msg))

            # Sanitize arguments
            if hasattr(record, "args") and record.args:
                sanitized_args = []
                for arg in record.args:
                    sanitized_args.append(self._sanitize_value(arg))
                record.args = tuple(sanitized_args)

        except Exception as e:
            # If sanitization fails, create a safe fallback message
            record.msg = f"<LOG_SANITIZATION_ERROR: {type(e).__name__}>"
            record.args = ()

        return True

    def _sanitize_value(self, value):
        """Sanitize any value type."""
        if isinstance(value, str):
            return self._sanitize_string(value)
        elif isinstance(value, dict):
            return self._sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            return self._sanitize_list(value)
        elif isinstance(value, bytes):
            return f"<BYTES:{len(value)} bytes>"
        else:
            return value

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string content to remove binary data."""
        if not isinstance(text, str):
            return str(text)

        # Check for very long strings that might be base64 data
        if len(text) > 1000:
            # Common base64 patterns (more comprehensive)
            base64_patterns = ["data:", "base64", "/9j/", "ggmp", "ivbor", "uff", "riff", "ftyp"]
            if any(pattern in text.lower() for pattern in base64_patterns):
                return f"<DATA:{len(text)} chars>"

            # Check for high ratio of base64-like characters (A-Z, a-z, 0-9, +, /, =)
            base64_chars = sum(1 for c in text if c.isalnum() or c in "+/=")
            if len(text) > 500 and base64_chars / len(text) > 0.8:
                return f"<LIKELY_BASE64:{len(text)} chars>"

            # JSON with large content
            if text.strip().startswith(("{", "[")):
                try:
                    import json

                    data = json.loads(text)
                    sanitized = self._sanitize_dict(data) if isinstance(data, dict) else self._sanitize_list(data)
                    return json.dumps(sanitized, indent=2)
                except:
                    return f"<JSON_DATA:{len(text)} chars>"

            # Other large content
            if len(text) > 2000:
                return f"<LARGE_STRING:{len(text)} chars>"

        return text

    def _sanitize_dict(self, data: dict) -> dict:
        """Recursively sanitize dictionary data."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            key_lower = str(key).lower()

            # Check if this key commonly contains binary data
            if any(binary_key in key_lower for binary_key in self.BINARY_DATA_KEYS):
                if isinstance(value, str) and len(value) > 100:
                    sanitized[key] = f"<{key.upper()}_DATA:{len(value)} chars>"
                elif isinstance(value, bytes):
                    sanitized[key] = f"<{key.upper()}_BYTES:{len(value)} bytes>"
                else:
                    sanitized[key] = self._sanitize_value(value)
            else:
                sanitized[key] = self._sanitize_value(value)

        return sanitized

    def _sanitize_list(self, data: list) -> list:
        """Sanitize list data."""
        sanitized = []
        for item in data:
            sanitized.append(self._sanitize_value(item))
        return sanitized


def setup_logging() -> logging.Logger:
    """Configure application-wide logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    logger.handlers.clear()

    # Create media data filter
    media_filter = MediaDataFilter()

    # Console handler with improved formatting
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    console.addFilter(media_filter)  # Add filter to prevent binary data logging
    logger.addHandler(console)

    # Last run file handler (overwrites each time)
    last_run_handler = logging.FileHandler(LOGS_DIR / "last_run.log", mode="w")  # Overwrite mode
    last_run_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    last_run_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"))
    last_run_handler.addFilter(media_filter)  # Add filter to prevent binary data logging
    logger.addHandler(last_run_handler)

    return logger


# Set up logging on import
setup_logging()
