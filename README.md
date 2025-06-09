# AudioInsight-CPP Prototype

This directory contains experimental prototypes for exploring alternative backends for AudioInsight using llama.cpp and multimodal models.

## Current Prototype: Ultravox Integration

### Overview
This prototype explores using llama.cpp with the Ultravox model for combined audio transcription and analysis. Unlike the main AudioInsight implementation that uses separate Whisper (transcription) + LLM (analysis) components, this approach uses a single multimodal model.

### Model: ultravox-v0_5-llama-3_2-1b-GGUF
- **Type**: Multimodal (audio + text)
- **Base**: Llama 3.2 1B Instruct
- **Features**: Audio understanding + text generation
- **Size**: ~762 MB (Q4_K quantized)
- **Context**: 131K tokens (4K active)

### Setup

1. **Install llama.cpp** (if not already installed):
```bash
# Clone and build llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j
```

2. **Start the server**:
```bash
./gpu-llama/build/bin/llama-server -hf ggml-org/ultravox-v0_5-llama-3_2-1b-GGUF:Q4_K_M --port 8081 -ngl -99
```

3. **Start the prototype**:
```bash
# Quick start - everything in one command
cd audioinsight-cpp && ./start_test.sh dev

# Or step by step:
# 1. Start llama-server
./start_test.sh server

# 2. In another terminal, serve the HTML interface
./start_test.sh html
# Then open http://localhost:3030/cpp.html in your browser
```

### Architecture Comparison

#### Current AudioInsight (Whisper + LLM)
```
Audio Input → Whisper (transcription) → LLM (analysis) → Results
```
- **Pros**: Specialized models, proven accuracy, streaming support
- **Cons**: Multiple models, more complex pipeline, higher resource usage

#### Ultravox Prototype (Single Model)
```
Audio Input → Ultravox (transcription + analysis) → Results
```
- **Pros**: Single model, simplified pipeline, lower memory usage
- **Cons**: Newer technology, less proven, may lack streaming capabilities

### Key Features to Test

1. **Audio Processing Quality**
   - Transcription accuracy vs Whisper
   - Audio format compatibility
   - Noise handling

2. **Analysis Capabilities**
   - Context understanding
   - Speaker analysis
   - Content insights

3. **Performance**
   - Inference speed
   - Memory usage
   - CPU vs GPU performance

4. **Integration**
   - API compatibility
   - Real-time processing
   - Error handling

### Development Notes

- The prototype uses the OpenAI-compatible API endpoints (`/v1/chat/completions`)
- Audio is converted to 16kHz mono PCM for optimal compatibility
- Fallback endpoints are implemented for different API versions
- CORS is handled through the llama-server configuration

### Next Steps

1. Test basic audio transcription accuracy
2. Compare performance with current Whisper implementation
3. Evaluate real-time processing capabilities
4. Assess integration complexity with existing AudioInsight features
5. Consider hybrid approaches (Ultravox for some features, Whisper for others)

### Files

- `../cpp.html` - Web interface prototype for testing
- `README.md` - This documentation file  
- `test_ultravox.py` - Python API testing script with comprehensive test suite
- `start_test.sh` - Interactive launcher script for all testing modes
- `requirements.txt` - Python dependencies for testing
- `(future)` - Performance benchmarking tools
- `(future)` - API compatibility layer

### Usage Commands

The `start_test.sh` script provides convenient commands for all testing scenarios:

```bash
./start_test.sh dev         # Start everything (server + web interface)
./start_test.sh server      # Start llama-server only
./start_test.sh html [port] # Serve HTML interface (default: port 3030)
./start_test.sh health      # Check server status
./start_test.sh test        # Run Python API tests
./start_test.sh audio file  # Test specific audio file
./start_test.sh stop        # Stop background services
./start_test.sh help        # Show all commands
```

**Key Benefits of New Setup:**
- **Proper CORS handling** - HTML served on port 3030 can access llama-server on 8081
- **One-command startup** - `dev` mode starts everything automatically
- **Background management** - Server runs in background with proper cleanup
- **Multiple test modes** - Web interface, Python scripts, and CLI testing
- **Easy port configuration** - Serve HTML on custom ports if needed 