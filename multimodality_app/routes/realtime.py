import asyncio
import base64
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..llm import get_response
from ..media_processing import (
    encode_audio,
    encode_image,
    encode_raw_audio,
    encode_video,
    process_uploaded_audio,
)
from ..media_processing.utils import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    VIDEO_MIME_TYPES,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# WebSocket Message Schemas
class RealtimeConfig(BaseModel):
    """Configuration for real-time session."""

    modalities: List[str] = Field(default=["text"], description="Supported modalities: text, audio, image, video")
    instructions: Optional[str] = Field(default=None, description="System instructions for the session")
    voice: Optional[str] = Field(default="alloy", description="Voice for audio responses (future use)")
    input_audio_format: str = Field(default="pcm16", description="Audio input format")
    output_audio_format: str = Field(default="pcm16", description="Audio output format")
    input_audio_transcription: Optional[Dict] = Field(default=None, description="Audio transcription settings")
    turn_detection: Optional[Dict] = Field(default=None, description="Turn detection settings")
    tools: List[Dict] = Field(default_factory=list, description="Available tools")
    tool_choice: str = Field(default="auto", description="Tool choice strategy")
    temperature: float = Field(default=0.6, description="Response temperature")
    max_response_output_tokens: Optional[int] = Field(default=None, description="Max output tokens")


class RealtimeMessage(BaseModel):
    """Base real-time message structure."""

    event_id: Optional[str] = None
    type: str

    class Config:
        extra = "allow"  # Allow additional fields


class SessionUpdateMessage(RealtimeMessage):
    """Session configuration update message."""

    type: str = "session.update"
    session: RealtimeConfig


class InputAudioBufferAppendMessage(RealtimeMessage):
    """Audio buffer append message."""

    type: str = "input_audio_buffer.append"
    audio: str  # base64 encoded audio


class InputAudioBufferCommitMessage(RealtimeMessage):
    """Audio buffer commit message."""

    type: str = "input_audio_buffer.commit"


class ConversationItemCreateMessage(RealtimeMessage):
    """Create conversation item message."""

    type: str = "conversation.item.create"
    item: Dict


class ResponseCreateMessage(RealtimeMessage):
    """Create response message."""

    type: str = "response.create"
    response: Optional[Dict] = None


# Response Messages
class SessionCreatedMessage(BaseModel):
    """Session created response."""

    event_id: str
    type: str = "session.created"
    session: RealtimeConfig


class ErrorMessage(BaseModel):
    """Error response message."""

    event_id: str
    type: str = "error"
    error: Dict[str, Union[str, int]]


class ResponseMessage(BaseModel):
    """Response message."""

    event_id: str
    type: str
    response: Optional[Dict] = None

    class Config:
        extra = "allow"


class ConnectionManager:
    """Manages WebSocket connections and sessions."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection and initialize session."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.sessions[session_id] = {
            "config": RealtimeConfig(),
            "audio_buffer": b"",
            "conversation": [],
            "context": "",
        }
        logger.info(f"🔌 WebSocket connected: {session_id}")
        logger.debug(f"📊 Session initialized with config: {self.sessions[session_id]['config']}")

    def disconnect(self, session_id: str):
        """Remove connection and clean up session."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]
        logger.info(f"🔌 WebSocket disconnected: {session_id}")
        logger.debug(f"📊 Active connections: {len(self.active_connections)}")

    async def send_message(self, session_id: str, message: Dict):
        """Send message to specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            logger.debug(f"📤 Sending {message.get('type', 'unknown')} to session: {session_id}")
            await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: Dict):
        """Broadcast message to all connections."""
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")


manager = ConnectionManager()


async def process_audio_chunk(audio_data: bytes, session_id: str) -> str:
    """Process audio chunk and return transcription/response."""
    try:
        # Get session context for audio format
        session = manager.sessions.get(session_id, {})
        config = session.get("config", RealtimeConfig())

        # Determine audio format parameters from config
        input_format = config.input_audio_format
        sample_rate = 16000  # Default for PCM16
        channels = 1  # Mono
        sample_width = 2  # 16-bit = 2 bytes

        if input_format == "pcm16":
            sample_rate = 16000
            sample_width = 2
        elif input_format == "pcm24":
            sample_rate = 24000
            sample_width = 3

        logger.info(f"🎵 Processing {len(audio_data)} bytes of {input_format} audio")

        # Process raw audio data using new function
        audio_b64 = encode_raw_audio(audio_data, sample_rate, channels, sample_width)

        # Get instructions
        instructions = config.instructions or "Please transcribe and respond to this audio."

        # Use existing LLM integration
        logger.info(f"🤖 Sending audio to LLM with instructions: {instructions[:50]}...")
        response = get_response(text_input=instructions, audio_b64s=[audio_b64])

        logger.info(f"✅ Audio processing complete, response length: {len(response.content)} chars")
        return response.content

    except Exception as e:
        logger.error(f"❌ Error processing audio chunk: {e}", exc_info=True)
        raise


async def process_multimodal_input(
    text: Optional[str] = None,
    audio_data: Optional[bytes] = None,
    image_data: Optional[bytes] = None,
    video_data: Optional[bytes] = None,
    session_id: str = None,
) -> str:
    """Process multimodal input using existing LLM integration."""
    try:
        # Prepare inputs
        audio_b64s = []
        image_b64s = []
        video_b64s = []

        # Process audio if provided
        if audio_data:
            temp_audio = Path(tempfile.mktemp(suffix=".wav"))
            with open(temp_audio, "wb") as f:
                f.write(audio_data)
            audio_b64s.append(encode_audio(temp_audio))
            temp_audio.unlink()

        # Process image if provided
        if image_data:
            temp_image = Path(tempfile.mktemp(suffix=".png"))
            with open(temp_image, "wb") as f:
                f.write(image_data)
            image_b64s.append(encode_image(temp_image))
            temp_image.unlink()

        # Process video if provided
        if video_data:
            temp_video = Path(tempfile.mktemp(suffix=".mp4"))
            with open(temp_video, "wb") as f:
                f.write(video_data)
            video_b64s.append(encode_video(temp_video))
            temp_video.unlink()

        # Get session context
        session = manager.sessions.get(session_id, {})
        config = session.get("config", RealtimeConfig())
        instructions = config.instructions

        # Combine instructions with text input
        final_text = text
        if instructions:
            if text:
                final_text = f"{instructions}\n\nUser input: {text}"
            else:
                final_text = instructions

        # Use existing LLM integration
        response = get_response(
            text_input=final_text,
            audio_b64s=audio_b64s if audio_b64s else None,
            image_b64s=image_b64s if image_b64s else None,
            video_b64s=video_b64s if video_b64s else None,
        )

        return response.content

    except Exception as e:
        logger.error(f"❌ Error processing multimodal input: {e}", exc_info=True)
        raise


@router.websocket("/ws/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time multimodal inference.

    Compatible with OpenAI Realtime API format while using your existing LLM backend.
    Supports text, audio, image, and video inputs with streaming responses.
    """
    session_id = f"session_{id(websocket)}"

    try:
        await manager.connect(websocket, session_id)
        logger.info(f"🔌 WebSocket connection established: {session_id}")

        # Send session created message
        session_created = {
            "event_id": f"event_{session_id}_created",
            "type": "session.created",
            "session": manager.sessions[session_id]["config"].dict(),
        }
        await manager.send_message(session_id, session_created)

        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                event_type = message.get("type")
                event_id = message.get("event_id", f"event_{asyncio.get_event_loop().time()}")

                logger.info(f"📨 Received message type: {event_type} for session: {session_id}")
                logger.debug(f"📄 Message content: {json.dumps(message, indent=2)}")

                if event_type == "session.update":
                    # Update session configuration
                    session_config = message.get("session", {})
                    manager.sessions[session_id]["config"] = RealtimeConfig(**session_config)

                    response = {
                        "event_id": event_id,
                        "type": "session.updated",
                        "session": session_config,
                    }
                    logger.info(f"📤 Sending session.updated for session: {session_id}")
                    await manager.send_message(session_id, response)

                elif event_type == "input_audio_buffer.append":
                    # Append audio to buffer
                    audio_b64 = message.get("audio", "")
                    audio_data = base64.b64decode(audio_b64)
                    manager.sessions[session_id]["audio_buffer"] += audio_data

                    # Send acknowledgment
                    response = {"event_id": event_id, "type": "input_audio_buffer.appended"}
                    logger.info(f"🎵 Audio buffer appended ({len(audio_data)} bytes) for session: {session_id}")
                    await manager.send_message(session_id, response)

                elif event_type == "input_audio_buffer.commit":
                    # Process accumulated audio buffer
                    audio_buffer = manager.sessions[session_id]["audio_buffer"]

                    if audio_buffer:
                        try:
                            # Process audio and get response
                            logger.info(f"🎵 Processing audio buffer ({len(audio_buffer)} bytes) for session: {session_id}")
                            llm_response = await process_audio_chunk(audio_buffer, session_id)

                            # Send response
                            response = {
                                "event_id": event_id,
                                "type": "response.done",
                                "response": {
                                    "id": f"resp_{event_id}",
                                    "object": "realtime.response",
                                    "status": "completed",
                                    "output": [
                                        {
                                            "id": f"item_{event_id}",
                                            "object": "realtime.item",
                                            "type": "message",
                                            "role": "assistant",
                                            "content": [{"type": "text", "text": llm_response}],
                                        }
                                    ],
                                },
                            }
                            logger.info(f"🤖 Sending audio response for session: {session_id}")
                            logger.info(f"💬 AI Response: {llm_response[:100]}{'...' if len(llm_response) > 100 else ''}")
                            await manager.send_message(session_id, response)

                        except Exception as e:
                            error_response = {
                                "event_id": event_id,
                                "type": "error",
                                "error": {
                                    "type": "server_error",
                                    "code": "processing_failed",
                                    "message": str(e),
                                },
                            }
                            await manager.send_message(session_id, error_response)

                    # Clear audio buffer
                    manager.sessions[session_id]["audio_buffer"] = b""

                    # Send buffer cleared confirmation
                    response = {"event_id": event_id, "type": "input_audio_buffer.cleared"}
                    await manager.send_message(session_id, response)

                elif event_type == "conversation.item.create":
                    # Handle conversation item creation (text, image, video)
                    item = message.get("item", {})
                    item_type = item.get("type")

                    if item_type == "message":
                        # Store in conversation history
                        manager.sessions[session_id]["conversation"].append(item)

                        # Send item created confirmation
                        response = {
                            "event_id": event_id,
                            "type": "conversation.item.created",
                            "item": item,
                        }
                        logger.info(f"💬 Conversation item created for session: {session_id}")
                        await manager.send_message(session_id, response)

                elif event_type == "response.create":
                    # Generate response based on conversation
                    session_data = manager.sessions[session_id]
                    conversation = session_data["conversation"]

                    # Get the last user message for processing
                    last_message = None
                    for item in reversed(conversation):
                        if item.get("role") == "user":
                            last_message = item
                            break

                    if last_message:
                        content = last_message.get("content", [])

                        # Extract content for processing
                        text_content = ""
                        audio_data = None
                        image_data = None
                        video_data = None

                        for content_item in content:
                            content_type = content_item.get("type")

                            if content_type == "text":
                                text_content = content_item.get("text", "")
                                logger.debug(f"📝 Extracted text: {text_content[:50]}{'...' if len(text_content) > 50 else ''}")
                            elif content_type == "input_audio":
                                audio_b64 = content_item.get("audio", "")
                                audio_data = base64.b64decode(audio_b64)
                            elif content_type == "image":
                                image_b64 = content_item.get("image", "")
                                image_data = base64.b64decode(image_b64)
                            elif content_type == "video":
                                video_b64 = content_item.get("video", "")
                                video_data = base64.b64decode(video_b64)

                        try:
                            # Process using multimodal handler
                            logger.info(f"🧠 Processing multimodal input for session: {session_id}")
                            llm_response = await process_multimodal_input(
                                text=text_content or None,
                                audio_data=audio_data,
                                image_data=image_data,
                                video_data=video_data,
                                session_id=session_id,
                            )

                            # Send response
                            response = {
                                "event_id": event_id,
                                "type": "response.done",
                                "response": {
                                    "id": f"resp_{event_id}",
                                    "object": "realtime.response",
                                    "status": "completed",
                                    "output": [
                                        {
                                            "id": f"item_{event_id}",
                                            "object": "realtime.item",
                                            "type": "message",
                                            "role": "assistant",
                                            "content": [{"type": "text", "text": llm_response}],
                                        }
                                    ],
                                },
                            }
                            logger.info(f"🤖 Sending multimodal response for session: {session_id}")
                            logger.info(f"💬 AI Response: {llm_response[:100]}{'...' if len(llm_response) > 100 else ''}")
                            await manager.send_message(session_id, response)

                            # Add assistant response to conversation
                            assistant_item = {
                                "id": f"item_{event_id}",
                                "object": "realtime.item",
                                "type": "message",
                                "role": "assistant",
                                "content": [{"type": "text", "text": llm_response}],
                            }
                            manager.sessions[session_id]["conversation"].append(assistant_item)

                        except Exception as e:
                            error_response = {
                                "event_id": event_id,
                                "type": "error",
                                "error": {
                                    "type": "server_error",
                                    "code": "processing_failed",
                                    "message": str(e),
                                },
                            }
                            await manager.send_message(session_id, error_response)

                else:
                    # Unknown message type
                    logger.warning(f"Unknown message type: {event_type}")
                    error_response = {
                        "event_id": event_id,
                        "type": "error",
                        "error": {
                            "type": "invalid_request_error",
                            "code": "unknown_event_type",
                            "message": f"Unknown event type: {event_type}",
                        },
                    }
                    await manager.send_message(session_id, error_response)

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    "event_id": "error",
                    "type": "error",
                    "error": {
                        "type": "invalid_request_error",
                        "code": "invalid_json",
                        "message": "Invalid JSON format",
                    },
                }
                await manager.send_message(session_id, error_response)

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(session_id)


@router.get("/api/realtime/status")
async def get_realtime_status():
    """Get real-time WebSocket status."""
    return {
        "status": "active",
        "active_connections": len(manager.active_connections),
        "sessions": list(manager.sessions.keys()),
        "endpoint": "/ws/realtime",
        "supported_modalities": ["text", "audio", "image", "video"],
        "backend_compatible": True,
    }
