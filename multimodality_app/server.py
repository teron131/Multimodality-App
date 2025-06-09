import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not found, using system environment only")


class GeminiServerHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler for the Gemini audio interface."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from (current package directory)
        super().__init__(*args, directory=Path(__file__).parent, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        # Parse the URL
        parsed_path = urllib.parse.urlparse(self.path)

        # API endpoint to get configuration
        if parsed_path.path == "/api/config":
            self._handle_config_request()
            return

        # Redirect root to index.html
        if parsed_path.path == "/" or parsed_path.path == "":
            self.path = "/index.html"

        # Serve static files normally
        super().do_GET()

    def _handle_config_request(self):
        """Handle API configuration requests."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        # Get API key from environment
        api_key = os.getenv("GOOGLE_API_KEY", "")

        response = {"google_api_key": api_key, "has_key": bool(api_key), "server": "multimodality-app", "version": "1.0.0"}

        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        """Custom logging to show useful info."""
        if self.path == "/api/config":
            print(f"📡 API config requested from {self.client_address[0]}")
        elif self.path.endswith(".html"):
            print(f"🌐 Serving {self.path} to {self.client_address[0]}")


def start_server(port: int = 3030, host: str = "127.0.0.1") -> None:
    """Start the web server.

    Args:
        port: Port number to serve on
        host: Host address to bind to
    """
    print(f"🚀 Starting AudioInsight-Gemini server on {host}:{port}")
    print(f"📋 Open http://{host}:{port}/ in your browser")

    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if api_key:
        print(f"✅ Google API key found in environment")
    else:
        print(f"⚠️ No GOOGLE_API_KEY found in environment")
        print(f"💡 Add GOOGLE_API_KEY=your_key_here to your .env file")

    # Check if HTML file exists
    html_file = Path(__file__).parent / "index.html"
    if not html_file.exists():
        print(f"❌ HTML file not found: {html_file}")
        print(f"💡 Make sure index.html exists in the multimodality_app directory")
        return

    server = HTTPServer((host, port), GeminiServerHandler)
    try:
        print(f"🌐 Server running at http://{host}:{port}/")
        print(f"📁 Serving files from: {Path(__file__).parent}")
        print(f"⏹️ Press Ctrl+C to stop")
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped")
    finally:
        server.server_close()


def main():
    """Main entry point for the server."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3030
    start_server(port)


if __name__ == "__main__":
    main()
