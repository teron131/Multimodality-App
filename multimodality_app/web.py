"""
Web interface module for AudioInsight-Gemini.
Provides convenient functions to start the web server.
"""

from .server import start_server


def run_gemini_server(port: int = 3030, host: str = "127.0.0.1") -> None:
    """Start the Gemini web interface server.

    Args:
        port: Port number to serve on (default: 3030)
        host: Host address to bind to (default: 127.0.0.1)
    """
    start_server(port=port, host=host)


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3030
    run_gemini_server(port)
