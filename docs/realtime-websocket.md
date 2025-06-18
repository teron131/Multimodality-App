# Real-time WebSocket Inference

This document describes the real-time WebSocket inference system that allows for bidirectional communication with the multimodal AI backend.

## Overview

The real-time WebSocket system provides:

- **Real-time communication** with the AI backend
- **Multimodal support** for text, audio, images, and video
- **OpenAI API compatibility** for easy model switching
- **Session management** with configurable instructions
- **Streaming responses** for low-latency interactions

## Architecture

The system consists of:

1. **WebSocket Server** (`/ws/realtime`) - Handles persistent connections
2. **Session Management** - Maintains conversation state and configuration
3. **Media Processing** - Handles audio, image, and video data
4. **LLM Integration** - Uses existing `llm.py` for inference with OpenAI-compatible API

## WebSocket Endpoint

```
ws://localhost:8001/ws/realtime
```

## Message Format

All messages follow the OpenAI Realtime API format for compatibility:

### Session Management

#### Update Session
```json
{
    "event_id": "event_1",
    "type": "session.update",
    "session": {
        "instructions": "You are a helpful assistant.",
        "modalities": ["text", "audio", "image", "video"],
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {
            "model": "whisper-1"
        },
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 200
        },
        "tools": [],
        "tool_choice": "auto",
        "temperature": 0.8,
        "max_response_output_tokens": 4096
    }
}
```

### Conversation Items

#### Create Text Message
```json
{
    "event_id": "event_2",
    "type": "conversation.item.create",
    "item": {
        "id": "msg_1",
        "type": "message",
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Hello, how are you?"
            }
        ]
    }
}
```

#### Create Audio Message
```json
{
    "event_id": "event_3",
    "type": "conversation.item.create",
    "item": {
        "id": "msg_2",
        "type": "message",
        "role": "user",
        "content": [
            {
                "type": "input_audio",
                "audio": "base64_encoded_audio_data"
            }
        ]
    }
}
```

#### Create Image Message
```json
{
    "event_id": "event_4",
    "type": "conversation.item.create",
    "item": {
        "id": "msg_3",
        "type": "message",
        "role": "user",
        "content": [
            {
                "type": "image",
                "image": "base64_encoded_image_data"
            }
        ]
    }
}
```

### Response Generation

#### Request Response
```json
{
    "event_id": "event_5",
    "type": "response.create"
}
```

## Server Responses

### Session Created
```json
{
    "event_id": "event_1_response",
    "type": "session.created",
    "session": {
        "id": "sess_123",
        "object": "realtime.session",
        "model": "gpt-4o-realtime-preview",
        "modalities": ["text", "audio"],
        "instructions": "You are a helpful assistant.",
        "voice": "alloy",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": null,
        "turn_detection": null,
        "tools": [],
        "tool_choice": "auto",
        "temperature": 0.8,
        "max_response_output_tokens": 4096
    }
}
```

### Response Done
```json
{
    "event_id": "event_5_response",
    "type": "response.done",
    "response": {
        "id": "resp_123",
        "object": "realtime.response",
        "status": "completed",
        "status_details": null,
        "output": [
            {
                "id": "item_123",
                "object": "realtime.item",
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello! I'm doing well, thank you for asking. How can I help you today?"
                    }
                ]
            }
        ],
        "usage": {
            "total_tokens": 25,
            "input_tokens": 10,
            "output_tokens": 15
        }
    }
}
```

### Error Response
```json
{
    "event_id": "event_error",
    "type": "error",
    "error": {
        "type": "invalid_request_error",
        "code": "invalid_request",
        "message": "Invalid message format",
        "param": "content"
    }
}
```

## Usage Examples

### Python Client

```python
import asyncio
import websockets
import json
import base64

async def realtime_client():
    uri = "ws://localhost:8001/ws/realtime"
    
    async with websockets.connect(uri) as websocket:
        # Update session
        await websocket.send(json.dumps({
            "event_id": "event_1",
            "type": "session.update",
            "session": {
                "instructions": "You are a helpful assistant.",
                "modalities": ["text", "audio", "image"]
            }
        }))
        
        # Send text message
        await websocket.send(json.dumps({
            "event_id": "event_2",
            "type": "conversation.item.create",
            "item": {
                "id": "msg_1",
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": "Hello!"}]
            }
        }))
        
        # Request response
        await websocket.send(json.dumps({
            "event_id": "event_3",
            "type": "response.create"
        }))
        
        # Listen for responses
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'response.done':
                response = data['response']
                for item in response['output']:
                    for content in item['content']:
                        if content['type'] == 'text':
                            print(f"Assistant: {content['text']}")

# Run the client
asyncio.run(realtime_client())
```

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/realtime');

ws.onopen = function(event) {
    console.log('Connected to WebSocket');
    
    // Update session
    ws.send(JSON.stringify({
        event_id: 'event_1',
        type: 'session.update',
        session: {
            instructions: 'You are a helpful assistant.',
            modalities: ['text', 'audio', 'image']
        }
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data.type);
    
    if (data.type === 'response.done') {
        const response = data.response;
        response.output.forEach(item => {
            item.content.forEach(content => {
                if (content.type === 'text') {
                    console.log('Assistant:', content.text);
                }
            });
        });
    }
};

// Send text message
function sendText(text) {
    ws.send(JSON.stringify({
        event_id: `event_${Date.now()}`,
        type: 'conversation.item.create',
        item: {
            id: `msg_${Date.now()}`,
            type: 'message',
            role: 'user',
            content: [{ type: 'text', text: text }]
        }
    }));
    
    // Request response
    ws.send(JSON.stringify({
        event_id: `event_${Date.now()}`,
        type: 'response.create'
    }));
}
```

## Testing

### 1. Start the Server

```bash
./start.sh
# or
uv run python -m multimodality_app.server
```

### 2. Python Client Test

```bash
# Simple test
python examples/realtime_client.py test

# Interactive demo
python examples/realtime_client.py
```

### 3. Browser Client Test

Open `examples/realtime_client.html` in your browser and:

1. Click "Connect" to establish WebSocket connection
2. Update session instructions if needed
3. Send text messages, audio files, or images
4. View real-time responses

## Model Compatibility

The system is designed to be OpenAI API compatible, allowing you to switch between:

- **OpenAI GPT models** (gpt-4, gpt-3.5-turbo, etc.)
- **Google Gemini models** (via OpenAI-compatible endpoint)
- **Open source models** (Ollama, vLLM, etc.)

Simply update the `llm.py` configuration to point to different model endpoints while maintaining the same WebSocket interface.

## Configuration

### Environment Variables

```bash
# Model configuration
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1  # or your custom endpoint
OPENAI_MODEL=gpt-4o-mini

# Server configuration
SERVER_HOST=localhost
SERVER_PORT=8001

# Audio processing
WHISPER_MODEL=base
SAMPLE_RATE=16000

# Feature flags
ENABLE_AUDIO_PROCESSING=true
ENABLE_IMAGE_PROCESSING=true
ENABLE_VIDEO_PROCESSING=true
```

### Session Configuration

You can configure the real-time session with:

- **Instructions**: System prompt for the AI
- **Modalities**: Supported input/output types
- **Audio settings**: Format, transcription, voice activity detection
- **Model parameters**: Temperature, max tokens, etc.
- **Tools**: Function calling capabilities

## Performance Considerations

- **Connection pooling**: WebSocket connections are maintained per client
- **Memory management**: Sessions are cleaned up on disconnect
- **Media processing**: Large files are processed asynchronously
- **Rate limiting**: Consider implementing rate limits for production use
- **Scaling**: Use a WebSocket proxy (nginx) for multiple instances

## Error Handling

The system provides comprehensive error handling:

- **Connection errors**: Automatic reconnection on client side
- **Message validation**: Schema validation for all messages
- **Processing errors**: Graceful error responses
- **Resource cleanup**: Proper cleanup on disconnect

## Security Considerations

- **CORS**: Configure appropriate CORS settings
- **Authentication**: Add authentication middleware if needed
- **Rate limiting**: Implement rate limiting for production
- **Input validation**: All inputs are validated and sanitized
- **File size limits**: Configure appropriate file size limits

## Future Enhancements

Potential improvements:

- **Streaming audio**: Real-time audio streaming
- **Voice activity detection**: Server-side VAD
- **Multiple sessions**: Support for multiple concurrent sessions
- **Session persistence**: Save/restore session state
- **Advanced tools**: Function calling and tool integration
- **Metrics**: Performance monitoring and analytics 