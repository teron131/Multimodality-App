"""
Real-time WebSocket endpoints for live multimodal processing.

Provides OpenAI-compatible real-time API for streaming audio, video, and interactive processing.
"""

import base64
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..llm import get_response
from ..media_processing import encode_image, encode_raw_audio, process_uploaded_video
from ..schema import Realtime
from .utils import (
    log_llm_response,
    log_multimodal_response,
    log_processing_start,
    truncate_text,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _create_safe_message_for_logging(message: Dict) -> Dict:
    """Create a safe representation of WebSocket message for logging by filtering binary data."""
    if not isinstance(message, dict):
        return message

    safe_message = {}
    for key, value in message.items():
        if isinstance(value, str):
            # Check for base64 audio/image/video data
            if key in ("audio", "image", "video", "data", "content", "buffer") and len(value) > 50:
                safe_message[key] = f"<{key.upper()}_DATA:{len(value)} chars>"
            elif len(value) > 500:
                # Check for base64-like content
                base64_chars = sum(1 for c in value if c.isalnum() or c in "+/=")
                if base64_chars / len(value) > 0.7:  # High ratio of base64 chars
                    safe_message[key] = f"<BASE64_DATA:{len(value)} chars>"
                else:
                    safe_message[key] = f"{value[:100]}...({len(value)} total chars)"
            else:
                safe_message[key] = value
        elif isinstance(value, dict):
            safe_message[key] = _create_safe_message_for_logging(value)
        elif isinstance(value, list):
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
            "config": Realtime.Config(),
            "audio_buffer": b"",
            "video_buffer": b"",
            "conversation": [],
        }
        logger.info(f"🔌 WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove connection and clean up session."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]
        logger.info(f"🔌 WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: Dict):
        """Send message to specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            logger.debug(f"📤 Sending {message.get('type', 'unknown')} to session: {session_id}")
            await websocket.send_text(json.dumps(message))


manager = ConnectionManager()


async def invoke_media_content(
    audio_data: Optional[bytes] = None,
    image_data: Optional[bytes] = None,
    video_data: Optional[bytes] = None,
    text: Optional[str] = None,
    session_id: str = None,
) -> str:
    """Unified media content analysis with LLM for real-time content."""
    try:
        # Get session context
        session = manager.sessions.get(session_id, {})
        config = session.get("config", Realtime.Config())
        instructions = config.instructions

        # Prepare inputs for LLM
        audio_b64s = []
        image_b64s = []
        video_b64s = []

        # Process each media type
        if audio_data:
            audio_b64s.append(encode_raw_audio(audio_data))
            logger.info(f"🎵 Processing {len(audio_data)} bytes of audio")

        if image_data:
            temp_image = Path(tempfile.mktemp(suffix=".png"))
            try:
                with open(temp_image, "wb") as f:
                    f.write(image_data)
                image_b64s.append(encode_image(temp_image))
                logger.info(f"🖼️ Processing {len(image_data)} bytes of image")
            finally:
                if temp_image.exists():
                    temp_image.unlink()

        if video_data:
            video_b64, _ = process_uploaded_video(video_data, f"realtime_{session_id}.mp4")
            video_b64s.append(video_b64)
            logger.info(f"🎬 Processing {len(video_data)} bytes of video")

        # Combine instructions with text input
        final_text = text
        if instructions:
            if text:
                final_text = f"{instructions}\n\nUser input: {text}"
            else:
                final_text = instructions

        # Get LLM response
        response = get_response(
            text_input=final_text,
            audio_b64s=audio_b64s if audio_b64s else None,
            image_b64s=image_b64s if image_b64s else None,
            video_b64s=video_b64s if video_b64s else None,
        )

        # Log response with preview
        total_data_size = (len(audio_data) if audio_data else 0) + (len(image_data) if image_data else 0) + (len(video_data) if video_data else 0)
        content_types = []
        if audio_data:
            content_types.append("audio")
        if image_data:
            content_types.append("image")
        if video_data:
            content_types.append("video")
        if text:
            content_types.append("text")

        log_realtime_response("multimodal analysis", session_id, response.content, total_data_size, content_types)

        return response.content

    except Exception as e:
        logger.error(f"❌ Error invoking LLM for media content: {e}", exc_info=True)
        return f"Analysis temporarily unavailable. Error: {str(e)}"


def create_response_message(event_id: str, content: str, response_type: str = "response.done") -> Dict:
    """Create standardized response message."""
    return {
        "event_id": event_id,
        "type": response_type,
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
                    "content": [{"type": "text", "text": content}],
                }
            ],
        },
    }


def create_error_message(event_id: str, error_message: str, error_code: str = "processing_failed") -> Dict:
    """Create standardized error message."""
    return {
        "event_id": event_id,
        "type": "error",
        "error": {
            "type": "server_error",
            "code": error_code,
            "message": error_message,
        },
    }


async def handle_buffer_commit(session_id: str, event_id: str, buffer_type: str) -> Dict:
    """Handle buffer commit for audio or video."""
    session = manager.sessions[session_id]
    buffer_key = f"{buffer_type}_buffer"
    buffer_data = session[buffer_key]

    if not buffer_data:
        return {"event_id": event_id, "type": f"input_{buffer_type}_buffer.cleared"}

    try:
        logger.info(f"🔄 Processing {buffer_type} buffer ({len(buffer_data)} bytes) for session: {session_id}")

        # Process based on buffer type
        if buffer_type == "audio":
            response_content = await invoke_media_content(audio_data=buffer_data, session_id=session_id)
        elif buffer_type == "video":
            response_content = await invoke_media_content(video_data=buffer_data, session_id=session_id)
        else:
            raise ValueError(f"Unsupported buffer type: {buffer_type}")

        # Additional logging for buffer processing is handled in invoke_media_content
        return create_response_message(event_id, response_content)

    except Exception as e:
        logger.error(f"❌ {buffer_type.title()} processing error for session {session_id}: {e}")
        return create_error_message(event_id, f"Unable to process {buffer_type}. Please try again.")

    finally:
        # Clear buffer
        session[buffer_key] = b""


@router.websocket("/ws/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time multimodal inference."""
    session_id = f"session_{id(websocket)}"

    try:
        await manager.connect(websocket, session_id)

        # Send session created event
        session_config = Realtime.Config()
        session_created = {"event_id": f"event_{session_id}_created", "type": "session.created", "session": session_config.dict()}
        await manager.send_message(session_id, session_created)
        logger.info(f"✅ Session created with modalities: {session_config.modalities}")

        # Main message handling loop
        while True:
            try:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)

                event_type = message.get("type")
                event_id = message.get("event_id", f"event_{int(time.time() * 1000)}")

                logger.info(f"📨 Received message type: {event_type} for session: {session_id}")
                logger.debug(f"📨 Full message: {_create_safe_message_for_logging(message)}")

                # Handle different message types
                if event_type == "session.update":
                    # Update session configuration
                    session_config = message.get("session", {})
                    manager.sessions[session_id]["config"] = Realtime.Config(**session_config)
                    response = {
                        "event_id": event_id,
                        "type": "session.updated",
                        "session": session_config,
                    }
                    await manager.send_message(session_id, response)

                elif event_type == "input_audio_buffer.append":
                    # Append audio to buffer
                    audio_b64 = message.get("audio", "")
                    audio_data = base64.b64decode(audio_b64)
                    manager.sessions[session_id]["audio_buffer"] += audio_data
                    response = {"event_id": event_id, "type": "input_audio_buffer.appended"}
                    await manager.send_message(session_id, response)

                elif event_type == "input_audio_buffer.commit":
                    # Process audio buffer
                    response = await handle_buffer_commit(session_id, event_id, "audio")
                    await manager.send_message(session_id, response)
                    # Send buffer cleared confirmation
                    await manager.send_message(session_id, {"event_id": event_id, "type": "input_audio_buffer.cleared"})

                elif event_type == "input_video_buffer.append":
                    # Append video to buffer
                    video_b64 = message.get("video", "")
                    video_data = base64.b64decode(video_b64)
                    manager.sessions[session_id]["video_buffer"] += video_data
                    response = {"event_id": event_id, "type": "input_video_buffer.appended"}
                    await manager.send_message(session_id, response)

                elif event_type == "input_video_buffer.commit":
                    # Process video buffer
                    response = await handle_buffer_commit(session_id, event_id, "video")
                    await manager.send_message(session_id, response)
                    # Send buffer cleared confirmation
                    await manager.send_message(session_id, {"event_id": event_id, "type": "input_video_buffer.cleared"})

                elif event_type == "conversation.item.create":
                    # Handle conversation item creation
                    item = message.get("item", {})
                    manager.sessions[session_id]["conversation"].append(item)
                    response = {
                        "event_id": event_id,
                        "type": "conversation.item.created",
                        "item": item,
                    }
                    await manager.send_message(session_id, response)

                elif event_type == "response.create":
                    # Generate response based on conversation
                    session_data = manager.sessions[session_id]
                    conversation = session_data["conversation"]

                    # Get the last user message
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
                            elif content_type == "audio":
                                audio_data = base64.b64decode(content_item.get("audio", ""))
                            elif content_type == "image":
                                image_data = base64.b64decode(content_item.get("image", ""))
                            elif content_type == "video":
                                video_data = base64.b64decode(content_item.get("video", ""))

                        try:
                            content_types = [item.get("type") for item in content if item.get("type")]
                            total_size = (len(audio_data) if audio_data else 0) + (len(image_data) if image_data else 0) + (len(video_data) if video_data else 0)
                            logger.info(f"🔄 Processing multimodal input for session: {session_id} - Content types: {content_types} ({total_size} bytes)")

                            llm_response = await invoke_media_content(
                                audio_data=audio_data,
                                image_data=image_data,
                                video_data=video_data,
                                text=text_content or None,
                                session_id=session_id,
                            )

                            response = create_response_message(event_id, llm_response)
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
                            logger.error(f"❌ Multimodal processing error for session {session_id}: {e}")
                            error_response = create_error_message(event_id, "Unable to process your request. Please try again.")
                            await manager.send_message(session_id, error_response)

                else:
                    # Unknown message type
                    logger.warning(f"Unknown message type: {event_type}")
                    error_response = create_error_message(event_id, "Invalid request format. Please try again.", "unknown_event_type")
                    await manager.send_message(session_id, error_response)

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = create_error_message("error", "Invalid JSON format", "invalid_json")
                await manager.send_message(session_id, error_response)

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(session_id)


@router.websocket("/ws/realtime/video")
async def websocket_video_stream_endpoint(websocket: WebSocket):
    """Dedicated WebSocket endpoint for real-time video streaming."""
    session_id = f"video_session_{id(websocket)}"

    try:
        await websocket.accept()
        logger.info(f"🎬 Video streaming WebSocket connected: {session_id}")

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
                message = await websocket.receive_json()
                message_type = message.get("type")

                if message_type == "video_frame":
                    # Process individual video frame
                    frame_data = base64.b64decode(message.get("frame", ""))
                    frame_id = message.get("frame_id", int(time.time() * 1000))

                    try:
                        # Process frame as image
                        temp_frame = Path(tempfile.mktemp(suffix=".jpg"))
                        try:
                            with open(temp_frame, "wb") as f:
                                f.write(frame_data)
                            frame_b64 = encode_image(temp_frame)
                        finally:
                            if temp_frame.exists():
                                temp_frame.unlink()

                        # Get frame analysis
                        instructions = message.get("prompt", "Describe what you see in this video frame.")
                        response = get_response(text_input=instructions, image_b64s=[frame_b64])

                        # Log frame analysis with preview
                        log_realtime_response("video frame analysis", session_id, response.content, len(frame_data), ["video_frame"])

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
                        response_content = await invoke_media_content(video_data=video_data, session_id=session_id)
                        await websocket.send_json(
                            {
                                "type": "video_complete.analyzed",
                                "analysis": response_content,
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
        "backend_compatible": True,
        "openai_compatible": True,
    }


def log_realtime_response(operation: str, session_id: str, response_content: str, data_size: int = 0, content_types: list = None) -> None:
    """Log real-time LLM response with content preview."""
    clean_content = response_content.replace("\n", " ").replace("\r", " ")
    preview = truncate_text(clean_content, 100)

    if content_types:
        content_type_str = " + ".join(content_types)
        logger.info(f"⚡ {operation} complete [{session_id}]: {content_type_str} ({data_size} bytes) -> {preview}")
    else:
        logger.info(f"⚡ {operation} complete [{session_id}]: ({data_size} bytes) -> {preview}")
