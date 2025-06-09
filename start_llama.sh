#!/bin/bash

# Multimodality App - Llama CUDA Server Startup Script

echo "🚀 Starting Multimodality App with Llama CUDA..."

# Check if llama-cuda server is built
if [ ! -f "./llama-cuda/build/bin/llama-server" ]; then
    echo "❌ llama-cuda server not found!"
    echo "📋 Build it first with:"
    echo "   git clone https://github.com/ggml-org/llama.cpp.git llama-cuda"
    echo "   cd llama-cuda"
    echo "   mkdir build && cd build"
    echo "   cmake .. -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=\"86\" -DGGML_CUDA_FORCE_MMQ=OFF"
    echo "   make -j\$(nproc) llama-server"
    echo "   cd ../.."
    exit 1
fi

# Check if llama-cuda server is running
if ! curl -s http://localhost:8081/health >/dev/null 2>&1; then
    echo "🔄 Starting llama-cuda server..."
    
    # Start llama-cuda server in background
    export LD_LIBRARY_PATH="$(pwd)/llama-cuda/build/bin:$LD_LIBRARY_PATH"
    nohup ./llama-cuda/build/bin/llama-server \
        -hf ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q4_K_M \
        --port 8081 \
        -ngl -99 \
        --host 0.0.0.0 \
        > llama-server.log 2>&1 &
    
    LLAMA_PID=$!
    echo "📝 llama-cuda server started with PID: $LLAMA_PID"
    echo "📄 Logs: llama-server.log"
    
    # Wait for server to start
    echo "⏳ Waiting for llama-cuda server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8081/health >/dev/null 2>&1; then
            echo "✅ llama-cuda server is ready!"
            break
        fi
        sleep 1
    done
    
    if ! curl -s http://localhost:8081/health >/dev/null 2>&1; then
        echo "❌ llama-cuda server failed to start. Check llama-server.log"
        exit 1
    fi
else
    echo "✅ llama-cuda server already running on port 8081"
fi

# Start the main application server
echo "🚀 Starting Multimodality App server on port 3031..."
echo "🌐 Access the app at: http://localhost:3031"
echo "📊 Health check: http://localhost:3031/health"
echo "🔗 Llama server: http://localhost:8081"

# Add cleanup trap
cleanup() {
    echo "🛑 Shutting down servers..."
    if [ ! -z "$LLAMA_PID" ] && kill -0 $LLAMA_PID 2>/dev/null; then
        kill $LLAMA_PID
        echo "✅ llama-cuda server stopped"
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start the FastAPI application
python -m multimodality_app.server_llama 