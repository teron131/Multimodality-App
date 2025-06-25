#!/usr/bin/env bash

# Color codes for logging
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default values
DEFAULT_HOST="127.0.0.1"
DEFAULT_PORT="3030"
DEFAULT_WORKERS="4"

# Load environment variables from .env file
if [ -f .env ]; then
    echo -e "${GREEN}✅ Loading .env file${NC}"
    set -o allexport
    source .env
    set +o allexport
fi

# Use environment variables or defaults
HOST=${SERVER_HOST:-$DEFAULT_HOST}
PORT=${SERVER_PORT:-$DEFAULT_PORT}
WORKERS=${UVICORN_WORKERS:-$DEFAULT_WORKERS}

# Main function to start the server
start_server() {
    echo -e "${BLUE}🚀 Starting Multimodality App Server...${NC}"

    # Start the FastAPI server with uvicorn
    uvicorn multimodality_app.server:app --host "$HOST" --port "$PORT" --workers "$WORKERS" --log-level "info"
}

# Run the server
start_server