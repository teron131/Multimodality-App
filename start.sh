#!/bin/bash
# Multimodality App Server
# Interactive backend selection and server startup

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
DEFAULT_PORT=3030
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Menu options
BACKENDS=("Gemini API" "llama.cpp CUDA" "Exit")
SELECTED=0

# Load environment variables
load_env() {
    if [ -f ".env" ]; then
        echo -e "${GREEN}✅ Loading .env file${NC}"
        set -a
        source .env 2>/dev/null || true
        set +a
    else
        echo -e "${YELLOW}⚠️  No .env file found${NC}"
    fi
}

# Display header
show_header() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         🚀 Multimodality App         ║${NC}"
    echo -e "${BLUE}║            Backend Selection         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
    echo
}

# Display menu
show_menu() {
    echo -e "${CYAN}Select backend to use:${NC}"
    echo
    
    for i in "${!BACKENDS[@]}"; do
        local num=$((i + 1))
        if [ $i -eq $SELECTED ]; then
            echo -e "  ${GREEN}► $num) ${BACKENDS[$i]}${NC}"
        else
            echo -e "    $num) ${BACKENDS[$i]}"
        fi
    done
    
    echo
    echo -e "${GREEN}Press 1, 2, or 3 to select, or q to quit${NC}"
}

# Handle menu navigation
navigate_menu() {
    while true; do
        show_header
        show_menu

        # Read a single key
        read -rsn1 -t 60 key

        case "$key" in
            q|Q)
                SELECTED=2
                break
                ;;
            '1')
                SELECTED=0
                break
                ;;
            '2')
                SELECTED=1
                break
                ;;
            '3')
                SELECTED=2
                break
                ;;
        esac
    done
}

# Start Gemini backend
start_gemini() {
    echo -e "${BLUE}♊ Starting Gemini backend...${NC}"
    
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo -e "${RED}❌ GOOGLE_API_KEY not found in .env file${NC}"
        echo -e "${YELLOW}💡 Create .env file with: GOOGLE_API_KEY=your_key_here${NC}"
        exit 1
    fi
    
    export LLM_BACKEND=gemini
    echo -e "${GREEN}✅ Gemini backend configured${NC}"
}

# Start Llama backend
start_llama() {
    echo -e "${BLUE}🦙 Starting Llama CUDA backend...${NC}"
    
    BACKEND_PORT=${BACKEND_PORT:-8081}
    
    # Check if server binary exists
    if [ ! -f "./llama-cuda/build/bin/llama-server" ]; then
        echo -e "${RED}❌ Llama server not found!${NC}"
        echo -e "${YELLOW}💡 Build it first - see llama.md${NC}"
        exit 1
    fi
    
    # Check if already running
    if curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Llama server already running${NC}"
    else
        echo -e "${YELLOW}🔄 Starting Llama server...${NC}"
        
        export LD_LIBRARY_PATH="$(pwd)/llama-cuda/build/bin:$LD_LIBRARY_PATH"
        nohup ./llama-cuda/build/bin/llama-server \
            -hf ggml-org/${LLAMA_MODEL:-ultravox-v0_5-llama-3_2-1b}-GGUF:Q4_K_M \
            --port $BACKEND_PORT \
            --host localhost \
            -ngl -99 > llama-server.log 2>&1 &
        
        # Wait for startup
        echo -e "${YELLOW}⏳ Waiting for server...${NC}"
        for i in {1..30}; do
            if curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Llama server ready!${NC}"
                break
            fi
            sleep 1
        done
    fi
    
    export LLM_BACKEND=llama
    export BACKEND_PORT=$BACKEND_PORT
}

# Start main server
start_server() {
    local port=${1:-$DEFAULT_PORT}
    
    echo -e "${GREEN}🚀 Starting server on http://127.0.0.1:$port${NC}"
    echo -e "${YELLOW}📋 Press Ctrl+C to stop${NC}"
    echo
    
    cd "$SCRIPT_DIR"
    
    if command -v python3 > /dev/null; then
        python3 -m uvicorn multimodality_app.server:app \
            --host 127.0.0.1 \
            --port "$port" \
            --reload
    else
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi
}

# Main execution
main() {
    # Handle command line arguments
    if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        echo -e "${BLUE}Multimodality App Server${NC}"
        echo
        echo "Usage: $0 [port]"
        echo
        echo "Options:"
        echo "  port    Server port (default: 3030)"
        echo "  help    Show this help"
        echo "  debug   Enable debug mode for troubleshooting"
        echo
        echo "Interactive mode will start if no arguments provided."
        exit 0
    fi
    
    if [ "$1" = "debug" ]; then
        echo -e "${YELLOW}Starting key code debug mode...${NC}"
        echo -e "${YELLOW}Press Up Arrow, then Down Arrow, then 'q' to quit.${NC}"
        stty -icanon -echo
        while true; do
            read -rsn1 -t 60 key
            if [[ "$key" == $'\e' ]]; then
                read -rsn5 -t 0.01 rest
                key+="$rest"
            fi
            if [[ "$key" == "q" ]] || [[ "$key" == "Q" ]]; then
                break
            fi
            printf "Captured sequence: '%s' (quoted: %q)\n" "$key" "$key" | sed 's/\x1b/ESC/g'
        done
        stty icanon echo
        exit 0
    fi
    
    # Load environment
    load_env
    
    # Interactive mode
    navigate_menu
    
    case $SELECTED in
        0)  # Gemini
            clear
            start_gemini
            start_server "$1"
            ;;
        1)  # Llama
            clear
            start_llama
            start_server "$1"
            ;;
        2)  # Exit
            clear
            echo -e "${YELLOW}👋 Goodbye!${NC}"
            exit 0
            ;;
    esac
}

# Run main function
main "$@"