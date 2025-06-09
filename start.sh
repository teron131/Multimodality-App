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
    
    # Check for .env file and load environment variables safely
    if [ -f ".env" ]; then
        echo -e "${GREEN}✅ Found .env file${NC}"
        # Load .env file safely, ignoring comments and empty lines
        set -a  # Export all variables
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            # Only process lines that look like variable assignments
            if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
                eval "export $line"
            fi
        done < .env
        set +a  # Stop exporting
    else
        echo -e "${YELLOW}⚠️ No .env file found${NC}"
        echo -e "${YELLOW}💡 Create a .env file with configuration${NC}"
    fi
    
    # Check LLM backend configuration
    LLM_BACKEND=${LLM_BACKEND:-gemini}
    BACKEND_PORT=${BACKEND_PORT:-8081}
    
    if [ "$LLM_BACKEND" = "llama" ]; then
        echo -e "${BLUE}🦙 Using Llama backend on port $BACKEND_PORT${NC}"
        
        # Check if llama-cuda server is built
        if [ ! -f "./llama-cuda/build/bin/llama-server" ]; then
            echo -e "${RED}❌ llama-cuda server not found!${NC}"
            echo -e "${YELLOW}📋 Build it first with the commands in llama.md${NC}"
            return 1
        fi
        
        # Check if llama-cuda server is running
        if ! curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
            echo -e "${YELLOW}🔄 Starting llama-cuda server on localhost:$BACKEND_PORT...${NC}"
            
            # Start llama-cuda server in background
            export LD_LIBRARY_PATH="$(pwd)/llama-cuda/build/bin:$LD_LIBRARY_PATH"
            nohup ./llama-cuda/build/bin/llama-server \
                -hf ggml-org/${LLAMA_MODEL:-ultravox-v0_5-llama-3_2-1b}-GGUF:Q4_K_M \
                --port $BACKEND_PORT \
                --host localhost \
                -ngl -99 \
                > llama-server.log 2>&1 &
            
            LLAMA_PID=$!
            echo -e "${GREEN}📝 llama-cuda server started with PID: $LLAMA_PID${NC}"
            
            # Wait for server to start
            echo -e "${YELLOW}⏳ Waiting for llama-cuda server to start...${NC}"
            for i in {1..30}; do
                if curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
                    echo -e "${GREEN}✅ llama-cuda server is ready!${NC}"
                    break
                fi
                sleep 1
            done
            
            if ! curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
                echo -e "${RED}❌ llama-cuda server failed to start. Check llama-server.log${NC}"
                return 1
            fi
        else
            echo -e "${GREEN}✅ llama-cuda server already running on localhost:$BACKEND_PORT${NC}"
        fi
        
        # Add cleanup trap for llama server
        cleanup() {
            echo -e "\n${YELLOW}🛑 Shutting down servers...${NC}"
            if [ ! -z "$LLAMA_PID" ] && kill -0 $LLAMA_PID 2>/dev/null; then
                kill $LLAMA_PID
                echo -e "${GREEN}✅ llama-cuda server stopped${NC}"
            fi
            exit 0
        }
        trap cleanup SIGINT SIGTERM
        
    else
        echo -e "${BLUE}♊ Using Gemini backend${NC}"
        if [ -z "$GOOGLE_API_KEY" ]; then
            echo -e "${YELLOW}⚠️ Warning: GOOGLE_API_KEY not set${NC}"
            echo -e "${YELLOW}💡 Create a .env file with: GOOGLE_API_KEY=your_key_here${NC}"
        fi
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
    echo -e "  ${YELLOW}📁 Create .env file for Gemini:${NC}"
    echo -e "    LLM_BACKEND=gemini"
    echo -e "    GOOGLE_API_KEY=your_key_here"
    echo -e "    GEMINI_MODEL=gemini-2.5-flash-preview-05-20"
    echo -e "  ${YELLOW}📁 Create .env file for Llama:${NC}"
    echo -e "    LLM_BACKEND=llama"
    echo -e "    BACKEND_PORT=8081"
    echo -e "    LLAMA_MODEL=ultravox-v0_5-llama-3_2-1b"
    echo -e "  ${YELLOW}🔑 Get API Key:${NC}        https://aistudio.google.com/app/apikey"
    echo -e "  ${YELLOW}🦙 Build Llama CUDA:${NC}   See llama.md for instructions"
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