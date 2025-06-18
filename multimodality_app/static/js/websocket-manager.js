/**
 * WebSocket Connection Manager
 * Handles real-time communication with the server
 */

class WebSocketManager {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        
        // Bind methods to maintain context
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.sendMessage = this.sendMessage.bind(this);
        this.sendText = this.sendText.bind(this);
        this.sendAudioFile = this.sendAudioFile.bind(this);
        this.sendImageFile = this.sendImageFile.bind(this);
        this.sendVideoFile = this.sendVideoFile.bind(this);
    }

    connect() {
        const wsUrl = `ws://${window.location.host}/ws/realtime`;
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = (event) => {
            this.isConnected = true;
            this.updateStatus('Connected', 'connected');
            updateRealtimeMessage('✅ Connected to server successfully');
            this.enableControls(true);
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };
        
        this.websocket.onclose = (event) => {
            this.isConnected = false;
            this.updateStatus('Disconnected', 'ready');
            updateRealtimeMessage('❌ Disconnected from server');
            this.enableControls(false);
        };
        
        this.websocket.onerror = (error) => {
            updateRealtimeMessage(`❌ Connection error. Please try reconnecting.`);
            updateOutput(`❌ Connection Error: Unable to connect to server\n`);
        };
    }

    disconnect() {
        if (this.websocket) {
            this.websocket.close();
        }
    }

    handleMessage(message) {
        // Show user-friendly messages based on message type
        if (message.type === 'response.done' && message.response) {
            const output = message.response.output?.[0]?.content?.[0]?.text || 'No response received';
            updateOutput(`🤖 AI Response: ${output}\n`);
            updateRealtimeMessage(`✅ Response received from AI`);
        } else if (message.type === 'error') {
            updateRealtimeMessage(`❌ Server error: ${message.error?.message || 'Unknown error'}`);
        } else if (message.type === 'response.audio_transcript.delta') {
            updateRealtimeMessage(`🎵 Processing audio...`);
        } else if (message.type === 'conversation.item.created') {
            updateRealtimeMessage(`✅ Message processed by server`);
        } else {
            // For other message types, show a generic confirmation
            updateRealtimeMessage(`📨 Server response received`);
        }
    }

    updateStatus(text, status) {
        const statusElement = document.getElementById('wsStatusText');
        const statusContainer = document.getElementById('wsStatus');
        
        if (statusElement && statusContainer) {
            statusElement.textContent = text;
            statusContainer.className = `status-indicator status-${status}`;
        }
        
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        
        if (connectBtn) connectBtn.disabled = this.isConnected;
        if (disconnectBtn) disconnectBtn.disabled = !this.isConnected;
    }

    enableControls(enabled) {
        const controls = [
            'sendTextBtn', 'sendAudioBtn', 'sendImageBtn', 'sendVideoBtn',
            'realtimeAudioFile', 'realtimeImageFile', 'realtimeVideoFile',
            'realtimeVideoPrompt', 'videoStreamBtn', 'screenAnalysisPrompt', 
            'frameInterval', 'imageQuality', 'changeThreshold', 'testCaptureBtn',
            'realtimeRecordBtn'
        ];
        
        controls.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.disabled = !enabled;
            }
        });
    }

    sendMessage(message) {
        if (!this.isConnected || !this.websocket) {
            updateRealtimeMessage('❌ Not connected to server');
            return false;
        }
        
        this.websocket.send(JSON.stringify(message));
        return true;
    }

    sendText() {
        const textInput = document.getElementById('realtimeTextInput');
        if (!textInput) {
            updateRealtimeMessage('❌ Text input not found');
            return;
        }
        
        const text = textInput.value;
        if (!text.trim()) {
            updateRealtimeMessage('❌ Please enter some text');
            return;
        }
        
        const message = {
            event_id: `text_${Date.now()}`,
            type: 'conversation.item.create',
            item: {
                id: `item_${Date.now()}`,
                type: 'message',
                role: 'user',
                content: [{ type: 'text', text: text }]
            }
        };
        
        if (this.sendMessage(message)) {
            updateRealtimeMessage(`📤 Sent text: ${text}`);
            textInput.value = ''; // Clear input
            
            // Request response
            setTimeout(() => {
                const responseRequest = {
                    event_id: `response_${Date.now()}`,
                    type: 'response.create'
                };
                this.sendMessage(responseRequest);
            }, 100);
        }
    }

    async sendAudioFile() {
        const fileInput = document.getElementById('realtimeAudioFile');
        
        if (!fileInput) {
            updateRealtimeMessage('❌ Audio file input not found');
            return;
        }
        
        if (!fileInput.files[0]) {
            updateRealtimeMessage('❌ Please select an audio file');
            return;
        }
        
        try {
            const file = fileInput.files[0];
            updateRealtimeMessage(`📤 Sending audio file: ${file.name}`);
            
            const arrayBuffer = await file.arrayBuffer();
            const base64 = arrayBufferToBase64(arrayBuffer);
            
            const message = {
                event_id: `audio_${Date.now()}`,
                type: 'conversation.item.create',
                item: {
                    id: `item_${Date.now()}`,
                    type: 'message',
                    role: 'user',
                    content: [{ type: 'audio', audio: base64 }]
                }
            };
            
            if (this.sendMessage(message)) {
                updateRealtimeMessage(`✅ Audio file sent successfully`);
                
                // Request response
                setTimeout(() => {
                    const responseRequest = {
                        event_id: `response_${Date.now()}`,
                        type: 'response.create'
                    };
                    this.sendMessage(responseRequest);
                }, 100);
            }
        } catch (error) {
            updateRealtimeMessage(`❌ Failed to send audio file: ${error.message}`);
        }
    }

    async sendImageFile() {
        const fileInput = document.getElementById('realtimeImageFile');
        
        if (!fileInput) {
            updateRealtimeMessage('❌ Image file input not found');
            return;
        }
        
        if (!fileInput.files[0]) {
            updateRealtimeMessage('❌ Please select an image file');
            return;
        }
        
        try {
            const file = fileInput.files[0];
            updateRealtimeMessage(`📤 Sending image file: ${file.name}`);
            
            const arrayBuffer = await file.arrayBuffer();
            const base64 = arrayBufferToBase64(arrayBuffer);
            
            const message = {
                event_id: `image_${Date.now()}`,
                type: 'conversation.item.create',
                item: {
                    id: `item_${Date.now()}`,
                    type: 'message',
                    role: 'user',
                    content: [{ type: 'image', image: base64 }]
                }
            };
            
            if (this.sendMessage(message)) {
                updateRealtimeMessage(`✅ Image file sent successfully`);
                
                // Request response
                setTimeout(() => {
                    const responseRequest = {
                        event_id: `response_${Date.now()}`,
                        type: 'response.create'
                    };
                    this.sendMessage(responseRequest);
                }, 100);
            }
        } catch (error) {
            updateRealtimeMessage(`❌ Failed to send image file: ${error.message}`);
        }
    }

    async sendVideoFile() {
        const fileInput = document.getElementById('realtimeVideoFile');
        const promptInput = document.getElementById('realtimeVideoPrompt');
        
        if (!fileInput) {
            updateRealtimeMessage('❌ Video file input not found');
            return;
        }
        
        if (!fileInput.files[0]) {
            updateRealtimeMessage('❌ Please select a video file');
            return;
        }
        
        try {
            const file = fileInput.files[0];
            const prompt = promptInput ? promptInput.value : 'Analyze this video';
            updateRealtimeMessage(`📤 Sending video file: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
            
            const arrayBuffer = await file.arrayBuffer();
            const base64 = arrayBufferToBase64(arrayBuffer);
            
            // Send video with custom prompt
            const message = {
                event_id: `video_${Date.now()}`,
                type: 'conversation.item.create',
                item: {
                    id: `item_${Date.now()}`,
                    type: 'message',
                    role: 'user',
                    content: [
                        { type: 'video', video: base64 },
                        { type: 'text', text: prompt }
                    ]
                }
            };
            
            if (this.sendMessage(message)) {
                updateRealtimeMessage(`✅ Video file sent successfully`);
                
                // Request response
                setTimeout(() => {
                    const responseRequest = {
                        event_id: `response_${Date.now()}`,
                        type: 'response.create'
                    };
                    this.sendMessage(responseRequest);
                }, 100);
            }
        } catch (error) {
            updateRealtimeMessage(`❌ Failed to send video file: ${error.message}`);
        }
    }
}

// Create global instance
const webSocketManager = new WebSocketManager();

// Export functions for global access (maintain compatibility with HTML)
window.connectWebSocket = webSocketManager.connect;
window.disconnectWebSocket = webSocketManager.disconnect;
window.sendRealtimeText = webSocketManager.sendText;
window.sendRealtimeAudio = webSocketManager.sendAudioFile;
window.sendRealtimeImage = webSocketManager.sendImageFile;
window.sendRealtimeVideo = webSocketManager.sendVideoFile;

// Also export the manager instance for use by other modules
window.wsManager = webSocketManager; 