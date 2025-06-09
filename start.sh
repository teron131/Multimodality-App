#!/bin/bash
# AudioInsight-CPP Test Launcher
# This script provides easy commands to test the Ultravox integration.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🚀 AudioInsight-CPP Test Launcher${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if llama-server is running
check_server() {
    echo -e "\n${YELLOW}🔍 Checking llama-server status...${NC}"
    if curl -s http://127.0.0.1:8081/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ llama-server is running on port 8081${NC}"
        return 0
    else
        echo -e "${RED}❌ llama-server is not running on port 8081${NC}"
        echo -e "${YELLOW}💡 Use './start.sh server' to start it${NC}"
        return 1
    fi
}

# Start llama-server
start_server() {
    echo -e "\n${YELLOW}🚀 Starting llama-server...${NC}"
    
    # Check if already running
    if curl -s http://127.0.0.1:8081/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ llama-server is already running${NC}"
        return 0
    fi
    
    # Check if llama-server command exists
    if ! command -v llama-server > /dev/null; then
        echo -e "${RED}❌ llama-server command not found${NC}"
        echo -e "${YELLOW}💡 Please install llama.cpp first:${NC}"
        echo -e "   git clone https://github.com/ggerganov/llama.cpp"
        echo -e "   cd llama.cpp && make -j"
        echo -e "   # Add llama.cpp to your PATH"
        return 1
    fi
    
    echo -e "${BLUE}📥 Starting llama-server with Ultravox model...${NC}"
    echo -e "${YELLOW}   This will download the model if not cached (~762MB)${NC}"
    echo -e "${YELLOW}   Press Ctrl+C to stop the server${NC}"
    
    # Start the server
    ./llama-cuda/build/bin/llama-server -hf ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q4_K_M --port 8081 -ngl 99
}

# Function to run Python test
run_python_test() {
    echo -e "\n${YELLOW}🐍 Running Python test script...${NC}"
    cd "$SCRIPT_DIR"
    python3 test_ultravox.py "$@"
}

# Function to serve HTML prototype on a port
serve_html() {
    local port=${1:-3030}
    echo -e "\n${YELLOW}🌐 Starting web server for HTML prototype...${NC}"
    
    # Check if port is available
    if curl -s http://127.0.0.1:$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Port $port is already in use${NC}"
        echo -e "${BLUE}📋 Open http://127.0.0.1:$port/cpp.html in your browser${NC}"
        return 0
    fi
    
    # Start Python HTTP server
    echo -e "${GREEN}🚀 Starting web server on http://127.0.0.1:$port${NC}"
    echo -e "${BLUE}📋 Open http://127.0.0.1:$port/cpp.html in your browser${NC}"
    echo -e "${YELLOW}   Press Ctrl+C to stop the web server${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Use Python 3
    if command -v python3 > /dev/null; then
        python3 -m http.server $port
    else
        echo -e "${RED}❌ Python 3 not found. Cannot start web server.${NC}"
        echo -e "${YELLOW}📋 Please open this file manually: file://$PROJECT_ROOT/cpp.html${NC}"
        return 1
    fi
}

# Main menu
show_help() {
    echo -e "\n${BLUE}Available commands:${NC}"
    echo -e "  ${GREEN}./start.sh server${NC}      - Start llama-server with Ultravox model"
    echo -e "  ${GREEN}./start.sh health${NC}      - Check server health only"
    echo -e "  ${GREEN}./start.sh html [port]${NC} - Serve HTML prototype (default port: 3030)"
    echo -e "  ${GREEN}./start.sh reload${NC}      - Force reload HTML with cache busting"
    echo -e "  ${GREEN}./start.sh test${NC}        - Run comprehensive Python tests"
    echo -e "  ${GREEN}./start.sh audio <file>${NC} - Test specific audio file"
    echo -e "  ${GREEN}./start.sh debug <file>${NC} - Debug multimodal API approaches"
    echo -e "  ${GREEN}./start.sh dev${NC}         - Start both server and web interface"
    echo -e "  ${GREEN}./start.sh stop${NC}        - Stop background llama-server"
    echo -e "  ${GREEN}./start.sh help${NC}        - Show this help"
    echo -e "\n${BLUE}Examples:${NC}"
    echo -e "  ${YELLOW}./start.sh dev${NC}                    # Start everything"
    echo -e "  ${YELLOW}./start.sh server${NC}                 # Start llama-server only"
    echo -e "  ${YELLOW}./start.sh html 8080${NC}              # Serve HTML on port 8080"
    echo -e "  ${YELLOW}./start.sh test${NC}                   # Run Python tests"
    echo -e "  ${YELLOW}./start.sh audio ../audio/sample.wav${NC} # Test specific file"
}

# Parse command line arguments
case "${1:-help}" in
    "server")
        start_server
        ;;
    "health")
        check_server
        ;;
    "html")
        port=${2:-3030}
        serve_html "$port"
        ;;
    "reload")
        echo -e "\n${YELLOW}🔄 Force reloading HTML with cache busting...${NC}"
        
        # Update HTML title and content to force reload
        timestamp=$(date +"%Y%m%d_%H%M%S")
        
        # Backup original if it doesn't exist
        if [ ! -f "cpp.html.backup" ]; then
            cp cpp.html cpp.html.backup
        fi
        
        # Update title with timestamp
        sed -i "s/AudioInsight-CPP Prototype.*/AudioInsight-CPP Prototype - RELOAD $timestamp<\/title>/" cpp.html
        
        # Update debug messages
        sed -i "s/v2\.1 FORCE RELOAD/RELOAD_$timestamp/g" cpp.html
        
        echo -e "${GREEN}✅ HTML updated with timestamp: $timestamp${NC}"
        echo -e "${BLUE}📋 Now refresh your browser or open: http://127.0.0.1:3030/cpp.html?v=$timestamp${NC}"
        echo -e "${YELLOW}💡 Use Ctrl+Shift+R for hard refresh, or close tab and reopen${NC}"
        ;;
    "test")
        if check_server; then
            run_python_test "${@:2}"
        fi
        ;;
    "audio")
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please specify an audio file${NC}"
            echo -e "${YELLOW}Usage: ./start.sh audio <path_to_audio_file>${NC}"
            exit 1
        fi
        if check_server; then
            run_python_test --audio-file "$2" "${@:3}"
        fi
        ;;
    "debug")
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please specify an audio file for debugging${NC}"
            echo -e "${YELLOW}Usage: ./start.sh debug <path_to_audio_file>${NC}"
            exit 1
        fi
        if check_server; then
            echo -e "${YELLOW}🐛 Running multimodal API debugging...${NC}"
            cd "$SCRIPT_DIR"
            python3 -c "
from test_ultravox import UltravoxTester
from pathlib import Path
import json

tester = UltravoxTester()
audio_file = Path('$2')
if not audio_file.is_absolute():
    audio_file = Path('$2')  # Use relative to current working directory

print('🧪 Testing multimodal approaches...')
results = tester.test_multimodal_approaches(audio_file)

print('\n' + '='*60)
print('🔍 DEBUGGING RESULTS')
print('='*60)
for approach, result in results.items():
    print(f'\n📋 {approach.upper()}:')
    print(json.dumps(result, indent=2))
print('\n' + '='*60)
"
        fi
        ;;
    "dev")
        echo -e "${BLUE}🚀 Starting development environment...${NC}"
        echo -e "${YELLOW}   This will start both llama-server and web interface${NC}"
        echo -e "${YELLOW}   Use Ctrl+C to stop everything${NC}"
        
        # Start server in background if not running
        if ! check_server > /dev/null 2>&1; then
            echo -e "\n${YELLOW}📡 Starting llama-server in background...${NC}"
            nohup ./llama-cuda/build/bin/llama-server -hf ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q4_K_M --port 8081 -ngl 99 > llama-server.log 2>&1 &
            echo $! > llama-server.pid
            echo -e "${GREEN}✅ llama-server started (PID: $(cat llama-server.pid))${NC}"
            echo -e "${BLUE}📋 Server logs: ./llama-server.log${NC}"
            
            # Wait for server to start
            echo -e "${YELLOW}⏳ Waiting for server to start...${NC}"
            for i in {1..30}; do
                if curl -s http://127.0.0.1:8081/health > /dev/null 2>&1; then
                    echo -e "${GREEN}✅ Server is ready!${NC}"
                    break
                fi
                sleep 1
                echo -n "."
            done
            echo ""
        fi
        
        # Start web server (this will block)
        echo -e "\n${YELLOW}🌐 Starting web interface...${NC}"
        serve_html 3030
        ;;
    "stop")
        cleanup_dev
        ;;
    "help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

# Cleanup function for dev mode
cleanup_dev() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    
    # Kill background llama-server if we started it
    if [ -f llama-server.pid ]; then
        pid=$(cat llama-server.pid)
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🔚 Stopping llama-server (PID: $pid)${NC}"
            kill "$pid"
            sleep 2
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${RED}💀 Force killing llama-server${NC}"
                kill -9 "$pid"
            fi
        fi
        rm -f llama-server.pid
    fi
    
    # Remove log file if empty
    if [ -f llama-server.log ] && [ ! -s llama-server.log ]; then
        rm -f llama-server.log
    fi
    
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Trap cleanup on script exit for dev mode
if [ "${1:-help}" = "dev" ]; then
    trap cleanup_dev EXIT INT TERM
fi

echo -e "\n${GREEN}🏁 Done!${NC}" 