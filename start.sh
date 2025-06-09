#!/bin/bash
# AudioInsight-Gemini Web Server
# Simple script to serve the HTML prototype for testing Gemini API integration.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🚀 AudioInsight-Gemini Web Server${NC}"
echo -e "${BLUE}==================================${NC}"

# Function to serve HTML prototype
serve_html() {
    local port=${1:-3030}
    echo -e "\n${YELLOW}🌐 Starting AudioInsight-Gemini server...${NC}"
    
    # Check if port is available
    if curl -s http://127.0.0.1:$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Port $port is already in use${NC}"
        echo -e "${BLUE}📋 Open http://127.0.0.1:$port/ in your browser${NC}"
        return 0
    fi
    
    # Check for .env file
    if [ -f ".env" ]; then
        echo -e "${GREEN}✅ Found .env file${NC}"
    else
        echo -e "${YELLOW}⚠️ No .env file found${NC}"
        echo -e "${YELLOW}💡 Create a .env file with: GOOGLE_API_KEY=your_key_here${NC}"
    fi
    
    # Check if multimodality_app package exists
    if [ ! -d "multimodality_app" ]; then
        echo -e "${RED}❌ multimodality_app directory not found${NC}"
        echo -e "${YELLOW}💡 Make sure you're running this from the project root${NC}"
        return 1
    fi
    
    # Check if the server module exists
    if [ ! -f "multimodality_app/server.py" ]; then
        echo -e "${RED}❌ Server module not found at multimodality_app/server.py${NC}"
        return 1
    fi
    
    echo -e "${GREEN}🚀 Starting server on http://127.0.0.1:$port${NC}"
    echo -e "${BLUE}📋 Open http://127.0.0.1:$port/ in your browser${NC}"
    echo -e "${YELLOW}   Press Ctrl+C to stop the web server${NC}"
    
    cd "$SCRIPT_DIR"
    
    # Use FastAPI server with uvicorn
    if command -v python3 > /dev/null; then
        echo -e "${GREEN}🚀 Starting FastAPI server with automatic reload...${NC}"
        python3 -m uvicorn multimodality_app.server:app --host 127.0.0.1 --port "$port" --reload
    else
        echo -e "${RED}❌ Python 3 not found. Cannot start web server.${NC}"
        return 1
    fi
}

# Function to open browser automatically
open_browser() {
    local port=${1:-3030}
    local url="http://127.0.0.1:$port/cpp.html"
    
    echo -e "${BLUE}🌐 Attempting to open browser...${NC}"
    
    # Try to open browser based on OS
    if command -v xdg-open > /dev/null; then
        # Linux
        xdg-open "$url" 2>/dev/null &
    elif command -v open > /dev/null; then
        # macOS
        open "$url" 2>/dev/null &
    elif command -v start > /dev/null; then
        # Windows
        start "$url" 2>/dev/null &
    else
        echo -e "${YELLOW}📋 Please manually open: $url${NC}"
    fi
}

# Main menu
show_help() {
    echo -e "\n${BLUE}Available commands:${NC}"
    echo -e "  ${GREEN}./start.sh${NC}             - Start web server (default port: 3030)"
    echo -e "  ${GREEN}./start.sh [port]${NC}      - Start web server on specific port"
    echo -e "  ${GREEN}./start.sh dev${NC}         - Start server and open browser"
    echo -e "  ${GREEN}./start.sh help${NC}        - Show this help"
    echo -e "\n${BLUE}Examples:${NC}"
    echo -e "  ${YELLOW}./start.sh${NC}             # Start on port 3030"
    echo -e "  ${YELLOW}./start.sh 8080${NC}        # Start on port 8080"
    echo -e "  ${YELLOW}./start.sh dev${NC}         # Start and open browser"
    echo -e "\n${BLUE}Environment Setup:${NC}"
    echo -e "  ${YELLOW}📁 Create .env file:${NC}   echo 'GOOGLE_API_KEY=your_key_here' > .env"
    echo -e "  ${YELLOW}🔑 Get API Key:${NC}        https://aistudio.google.com/app/apikey"
    echo -e "  ${YELLOW}🌐 Modern Browser:${NC}      Chrome, Firefox, Safari, or Edge"
    echo -e "  ${YELLOW}🎙️ Microphone Access:${NC}   Browser will request permission"
}

# Parse command line arguments
case "${1:-serve}" in
    "dev")
        port=${2:-3030}
        echo -e "${BLUE}🚀 Starting development mode...${NC}"
        
        # Start server in background
        echo -e "${YELLOW}🌐 Starting web server in background...${NC}"
        serve_html "$port" &
        server_pid=$!
        
        # Wait a moment for server to start
        sleep 3
        
        # Open browser
        open_browser "$port"
        
        # Wait for background server
        echo -e "${GREEN}✅ Development server running (PID: $server_pid)${NC}"
        echo -e "${YELLOW}   Press Ctrl+C to stop${NC}"
        wait $server_pid
        ;;
    "help")
        show_help
        ;;
    [0-9]*)
        # If first argument is a number, treat it as port
        serve_html "$1"
        ;;
    *)
        # Default: start server
        if [ "$1" != "serve" ] && [ -n "$1" ]; then
            echo -e "${RED}❌ Unknown command: $1${NC}"
            show_help
            exit 1
        fi
        port=${2:-3030}
        serve_html "$port"
        ;;
esac 