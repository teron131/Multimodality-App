"""
Real-time WebSocket endpoints for live multimodal processing.

Provides OpenAI-compatible real-time API for streaming audio, video, and interactive processing.
"""

import asyncio
import base64
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..llm import get_response
from ..media_processing import (
    encode_audio,
    encode_image,
    encode_raw_audio,
    process_uploaded_video,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _create_safe_message_for_logging(message: Dict) -> Dict:
    """Create a safe representation of WebSocket message for logging by filtering binary data.

    This function provides additional WebSocket-specific filtering beyond the global MediaDataFilter.
    """
    if not isinstance(message, dict):
        return message

    safe_message = {}

    for key, value in message.items():
        if isinstance(value, str):
            # Check for base64 audio/image/video data - more aggressive filtering for WebSocket messages
            if key in ("audio", "image", "video", "data", "content", "buffer") and len(value) > 50:
                safe_message[key] = f"<{key.upper()}_DATA:{len(value)} chars>"
            elif len(value) > 500:
                # Check for base64-like content
                base64_chars = sum(1 for c in value if c.isalnum() or c in "+/=")
                if base64_chars / len(value) > 0.7:  # High ratio of base64 chars
                    safe_message[key] = f"<BASE64_DATA:{len(value)} chars>"
                elif any(pattern in value.lower() for pattern in ["data:", "/9j/", "ggmp", "ivbor"]):
                    safe_message[key] = f"<BINARY_DATA:{len(value)} chars>"
                else:
                    # Truncate very long strings
                    safe_message[key] = f"{value[:100]}...({len(value)} total chars)"
            else:
                safe_message[key] = value
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            safe_message[key] = _create_safe_message_for_logging(value)
        elif isinstance(value, list):
            # Process lists, checking each item
            safe_list = []
            for item in value:
                if isinstance(item, dict):
                    safe_list.append(_create_safe_message_for_logging(item))
                elif isinstance(item, str) and len(item) > 500:
                    safe_list.append(f"<LIST_ITEM:{len(item)} chars>")
                else:
                    safe_list.append(item)
            safe_message[key] = safe_list
        elif isinstance(value, bytes):
            safe_message[key] = f"<BYTES:{len(value)} bytes>"
        else:
            safe_message[key] = value

    return safe_message


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


class InputVideoBufferAppendMessage(RealtimeMessage):
    """Video buffer append message."""

    type: str = "input_video_buffer.append"
    video: str  # base64 encoded video


class InputVideoBufferCommitMessage(RealtimeMessage):
    """Video buffer commit message."""

    type: str = "input_video_buffer.commit"


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
            "video_buffer": b"",
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

        # Get audio format from config
        input_format = config.input_audio_format
        logger.info(f"🎵 Processing {len(audio_data)} bytes of {input_format} audio")

        # Process raw audio data using simplified function
        audio_b64 = encode_raw_audio(audio_data)

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


async def process_video_chunk(video_data: bytes, session_id: str) -> str:
    """Process video chunk for real-time inference using unified Gemini-safe processing.

    Note: Gemini rejects small video chunks (< 1MB), so we accumulate them into larger videos.
    """
    try:
        logger.info(f"🎬 Processing video chunk: {len(video_data)} bytes for session: {session_id}")

        # Check if chunk is too small for Gemini (< 1MB threshold)
        chunk_size_mb = len(video_data) / (1024 * 1024)
        if chunk_size_mb < 0.1:
            logger.warning(f"⚠️ Video chunk too small ({chunk_size_mb:.1f}MB) - Gemini rejects small chunks. Skipping processing.")
            return "Video chunk received but too small for analysis. Recording longer clips for better results."

        # Use unified video processing (Gemini-safe)
        video_b64, encoding_info = process_uploaded_video(video_data, f"realtime_chunk_{session_id}.mp4")

        # Get session context
        session = manager.sessions.get(session_id, {})
        config = session.get("config", RealtimeConfig())
        instructions = config.instructions or "Analyze this video content."

        # Process with LLM
        response = get_response(
            text_input=instructions,
            video_b64s=[video_b64],
        )

        logger.info(f"🤖 Video processing complete for session: {session_id} (Gemini-safe: {encoding_info.get('meets_gemini_requirements', False)})")
        return response.content

    except Exception as e:
        logger.error(f"❌ Error processing video chunk: {e}", exc_info=True)
        # Return user-friendly error instead of raising
        return f"Video processing temporarily unavailable. Error: {str(e)}"


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

        # Process video if provided (unified Gemini-safe)
        if video_data:
            video_b64, _ = process_uploaded_video(video_data, f"multimodal_{session_id}.mp4")
            video_b64s.append(video_b64)

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
    try:
        # Initialize session
        session_id = f"session_{id(websocket)}"
        await manager.connect(websocket, session_id)

        # Send session created event
        session_config = RealtimeConfig()
        session_created = SessionCreatedMessage(event_id=f"event_{session_id}_created", session=session_config)
        await manager.send_message(session_id, session_created.dict())
        logger.info(f"🔌 WebSocket connection established: {session_id}")
        logger.info(f"✅ Session created with modalities: {session_config.modalities}")

        # Main message handling loop
        while True:
            try:
                # Receive message
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)

                event_type = message.get("type")
                event_id = message.get("event_id", f"event_{int(time.time() * 1000)}")

                logger.info(f"📨 Received message type: {event_type} for session: {session_id}")
                logger.debug(f"📨 Full message: {_create_safe_message_for_logging(message)}")

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
                            # Log technical error for developers
                            logger.error(f"❌ Audio processing error for session {session_id}: {e}")
                            error_response = {
                                "event_id": event_id,
                                "type": "error",
                                "error": {
                                    "type": "server_error",
                                    "code": "processing_failed",
                                    "message": "Unable to process audio. Please try again.",
                                },
                            }
                            await manager.send_message(session_id, error_response)

                    # Clear audio buffer
                    manager.sessions[session_id]["audio_buffer"] = b""

                    # Send buffer cleared confirmation
                    response = {"event_id": event_id, "type": "input_audio_buffer.cleared"}
                    await manager.send_message(session_id, response)

                elif event_type == "input_video_buffer.append":
                    # Append video to buffer
                    video_b64 = message.get("video", "")
                    video_data = base64.b64decode(video_b64)
                    manager.sessions[session_id]["video_buffer"] += video_data

                    # Send acknowledgment
                    response = {"event_id": event_id, "type": "input_video_buffer.appended"}
                    logger.info(f"🎬 Video buffer appended ({len(video_data)} bytes) for session: {session_id}")
                    await manager.send_message(session_id, response)

                elif event_type == "input_video_buffer.commit":
                    # Process accumulated video buffer
                    video_buffer = manager.sessions[session_id]["video_buffer"]

                    if video_buffer:
                        try:
                            # Process video and get response
                            logger.info(f"🎬 Processing video buffer ({len(video_buffer)} bytes) for session: {session_id}")
                            llm_response = await process_video_chunk(video_buffer, session_id)

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
                            logger.info(f"🤖 Sending video response for session: {session_id}")
                            logger.info(f"💬 AI Response: {llm_response[:100]}{'...' if len(llm_response) > 100 else ''}")
                            await manager.send_message(session_id, response)

                        except Exception as e:
                            # Log technical error for developers
                            logger.error(f"❌ Video processing error for session {session_id}: {e}")
                            error_response = {
                                "event_id": event_id,
                                "type": "error",
                                "error": {
                                    "type": "server_error",
                                    "code": "processing_failed",
                                    "message": "Unable to process video. Please try again.",
                                },
                            }
                            await manager.send_message(session_id, error_response)

                    # Clear video buffer
                    manager.sessions[session_id]["video_buffer"] = b""

                    # Send buffer cleared confirmation
                    response = {"event_id": event_id, "type": "input_video_buffer.cleared"}
                    await manager.send_message(session_id, response)

                elif event_type == "conversation.item.create":
                    # Handle conversation item creation (text, image, video)
                    item = message.get("item", {})
                    item_type = item.get("type")

                    if item_type == "message":
                        # Log UI file selection events
                        content = item.get("content", [])
                        for content_item in content:
                            content_type = content_item.get("type")
                            if content_type == "audio":
                                audio_b64 = content_item.get("audio", "")
                                size_mb = len(audio_b64) * 3 / 4 / (1024 * 1024)  # Approximate size from base64
                                logger.info(f"🎵 UI: Audio file uploaded - {size_mb:.2f} MB base64 data")
                            elif content_type == "image":
                                image_b64 = content_item.get("image", "")
                                size_mb = len(image_b64) * 3 / 4 / (1024 * 1024)  # Approximate size from base64
                                logger.info(f"🖼️ UI: Image file uploaded - {size_mb:.2f} MB base64 data")
                            elif content_type == "video":
                                video_b64 = content_item.get("video", "")
                                size_mb = len(video_b64) * 3 / 4 / (1024 * 1024)  # Approximate size from base64
                                logger.info(f"🎬 UI: Video file uploaded - {size_mb:.2f} MB base64 data")
                            elif content_type == "text":
                                text_content = content_item.get("text", "")
                                logger.info(f"📝 UI: Text message sent - {len(text_content)} chars")

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
                            elif content_type == "audio":
                                audio_b64 = content_item.get("audio", "")
                                audio_data = base64.b64decode(audio_b64)
                                logger.debug(f"🎵 Extracted audio: {len(audio_data)} bytes")
                            elif content_type == "image":
                                image_b64 = content_item.get("image", "")
                                image_data = base64.b64decode(image_b64)
                                logger.debug(f"🖼️ Extracted image: {len(image_data)} bytes")
                            elif content_type == "video":
                                video_b64 = content_item.get("video", "")
                                video_data = base64.b64decode(video_b64)
                                logger.debug(f"🎬 Extracted video: {len(video_data)} bytes")

                        try:
                            # Process using multimodal handler
                            content_types = [item.get("type") for item in content if item.get("type")]
                            logger.info(f"🧠 Processing multimodal input for session: {session_id} - Content types: {content_types}")

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
                            # Log technical error for developers
                            logger.error(f"❌ Multimodal processing error for session {session_id}: {e}")
                            error_response = {
                                "event_id": event_id,
                                "type": "error",
                                "error": {"type": "server_error", "code": "processing_failed", "message": "Unable to process your request. Please try again."},
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
                            "message": "Invalid request format. Please try again.",
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


@router.websocket("/ws/realtime/video")
async def websocket_video_stream_endpoint(websocket: WebSocket):
    """
    Dedicated WebSocket endpoint for real-time video streaming and inference.

    Optimized for live video processing with immediate frame-by-frame analysis.
    """
    try:
        session_id = f"video_session_{id(websocket)}"
        await websocket.accept()
        logger.info(f"🎬 Video streaming WebSocket connected: {session_id}")

        # Initialize video session
        manager.sessions[session_id] = {
            "config": RealtimeConfig(modalities=["video", "text"]),
            "video_buffer": b"",
            "frame_count": 0,
            "conversation": [],
            "context": "",
        }

        # Send connection confirmation
        await websocket.send_json(
            {
                "type": "video_stream.connected",
                "session_id": session_id,
                "status": "ready",
                "supported_formats": ["mp4", "webm", "avi"],
            }
        )

        while True:
            try:
                # Receive video frame or command
                message = await websocket.receive_json()
                message_type = message.get("type")

                if message_type == "video_frame":
                    # Process individual video frame
                    frame_data = base64.b64decode(message.get("frame", ""))
                    frame_id = message.get("frame_id", manager.sessions[session_id]["frame_count"])

                    manager.sessions[session_id]["frame_count"] += 1

                    logger.debug(f"🎬 Processing video frame {frame_id}: {len(frame_data)} bytes")

                    try:
                        # Process frame
                        temp_frame = Path(tempfile.mktemp(suffix=".jpg"))
                        with open(temp_frame, "wb") as f:
                            f.write(frame_data)

                        # Use image processing for individual frames
                        from ..media_processing import encode_image

                        frame_b64 = encode_image(temp_frame)
                        temp_frame.unlink()

                        # Get frame analysis
                        instructions = message.get("prompt", "Describe what you see in this video frame.")
                        response = get_response(
                            text_input=instructions,
                            image_b64s=[frame_b64],
                        )

                        # Send frame analysis
                        await websocket.send_json(
                            {
                                "type": "video_frame.analyzed",
                                "frame_id": frame_id,
                                "analysis": response.content,
                                "timestamp": time.time(),
                            }
                        )

                    except Exception as e:
                        logger.error(f"❌ Frame processing error: {e}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "frame_id": frame_id,
                                "message": "Frame processing failed",
                            }
                        )

                elif message_type == "video_complete":
                    # Process complete video
                    video_data = base64.b64decode(message.get("video", ""))

                    try:
                        llm_response = await process_video_chunk(video_data, session_id)

                        await websocket.send_json(
                            {
                                "type": "video_complete.analyzed",
                                "analysis": llm_response,
                                "timestamp": time.time(),
                            }
                        )

                    except Exception as e:
                        logger.error(f"❌ Video processing error: {e}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "Video processing failed",
                            }
                        )

                elif message_type == "ping":
                    # Health check
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": time.time(),
                        }
                    )

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in video stream: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"🎬 Video streaming WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ Video streaming WebSocket error: {e}", exc_info=True)
    finally:
        if session_id in manager.sessions:
            del manager.sessions[session_id]


@router.get("/api/realtime/status")
async def get_realtime_status():
    """Get real-time WebSocket status."""
    return {
        "status": "active",
        "active_connections": len(manager.active_connections),
        "sessions": list(manager.sessions.keys()),
        "endpoints": {
            "multimodal": "/ws/realtime",
            "video_streaming": "/ws/realtime/video",
        },
        "supported_modalities": ["text", "audio", "image", "video"],
        "video_features": {
            "buffer_support": True,
            "frame_by_frame": True,
            "complete_video": True,
            "streaming": True,
        },
        "backend_compatible": True,
        "openai_compatible": True,
    }
