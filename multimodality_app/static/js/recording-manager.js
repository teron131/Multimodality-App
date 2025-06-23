/**
 * Recording Manager
 * Handles audio recording functionality
 */

class RecordingManager {
    constructor() {
        // Regular recording
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.recordingStartTime = null;
        this.recordingInterval = null;
        
        // Real-time recording
        this.realtimeMediaRecorder = null;
        this.realtimeRecordedChunks = [];
        
        // Bind methods to maintain context
        this.start = this.start.bind(this);
        this.stop = this.stop.bind(this);
        this.startRealtime = this.startRealtime.bind(this);
        this.stopRealtime = this.stopRealtime.bind(this);
        this.updateRecordingTime = this.updateRecordingTime.bind(this);
        this.processRecorded = this.processRecorded.bind(this);
        this.sendRealtimeRecording = this.sendRealtimeRecording.bind(this);
    }

    async start() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.recordedChunks = [];
            this.mediaRecorder = new MediaRecorder(stream);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                stream.getTracks().forEach(track => track.stop());
                this.processRecorded();
            };
            
            this.mediaRecorder.start();
            this.recordingStartTime = Date.now();
            
            const recordBtn = document.getElementById('recordBtn');
            const stopBtn = document.getElementById('stopBtn');
            
            if (recordBtn) recordBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
            
            this.recordingInterval = setInterval(this.updateRecordingTime, 1000);
            updateOutput('🎙️ Recording started...\n');
            
        } catch (error) {
            updateOutput(`❌ Recording Error: ${error.message}\n`);
        }
    }
    
    stop() {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            clearInterval(this.recordingInterval);
            
            const recordBtn = document.getElementById('recordBtn');
            const stopBtn = document.getElementById('stopBtn');
            const recordingTime = document.getElementById('recordingTime');
            
            if (recordBtn) recordBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            if (recordingTime) recordingTime.textContent = '00:00';
            
            updateOutput('⏹️ Recording stopped, processing...\n');
        }
    }
    
    updateRecordingTime() {
        if (!this.recordingStartTime) return;
        
        const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        const recordingTime = document.getElementById('recordingTime');
        if (recordingTime) {
            recordingTime.textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    async processRecorded() {
        const audioBlob = new Blob(this.recordedChunks, { type: 'audio/webm' });
        const promptInput = document.getElementById('audioPrompt');
        const prompt = promptInput ? promptInput.value : 'Please transcribe this audio recording.';
        
        showProgress();

        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            formData.append('prompt', prompt);
            
            const response = await fetch('/api/invoke-audio', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Unable to process recording. Please try recording again.`);
            }
            
            const result = await response.json();
            updateOutput(`✅ Recording Processing Complete:\n${result.transcription}\n`);
        } catch (error) {
            updateOutput(`❌ Recording Processing Error: ${error.message}\n`);
        } finally {
            hideProgress();
        }
    }

    async startRealtime() {
        // Check if connected to WebSocket
        if (!webSocketManager || !webSocketManager.isConnected) {
            updateRealtimeMessage('❌ Please connect to server first');
            return;
        }
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.realtimeRecordedChunks = [];
            this.realtimeMediaRecorder = new MediaRecorder(stream);
            
            this.realtimeMediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.realtimeRecordedChunks.push(event.data);
                }
            };
            
            this.realtimeMediaRecorder.onstop = () => {
                stream.getTracks().forEach(track => track.stop());
                this.sendRealtimeRecording();
            };
            
            this.realtimeMediaRecorder.start();
            
            const recordBtn = document.getElementById('realtimeRecordBtn');
            const stopBtn = document.getElementById('realtimeStopBtn');
            
            if (recordBtn) recordBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
            
            updateRealtimeMessage('🎙️ Real-time recording started...');
            
        } catch (error) {
            updateRealtimeMessage(`❌ Recording Error: ${error.message}`);
        }
    }

    stopRealtime() {
        if (this.realtimeMediaRecorder && this.realtimeMediaRecorder.state === 'recording') {
            this.realtimeMediaRecorder.stop();
            
            const recordBtn = document.getElementById('realtimeRecordBtn');
            const stopBtn = document.getElementById('realtimeStopBtn');
            
            if (recordBtn) recordBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            
            updateRealtimeMessage('⏹️ Real-time recording stopped, sending...');
        }
    }
    
    async sendRealtimeRecording() {
        const audioBlob = new Blob(this.realtimeRecordedChunks, { type: 'audio/webm' });
        const arrayBuffer = await audioBlob.arrayBuffer();
        const base64 = arrayBufferToBase64(arrayBuffer);
        
        const message = {
            event_id: `live_audio_${Date.now()}`,
            type: 'conversation.item.create',
            item: {
                id: `item_${Date.now()}`,
                type: 'message',
                role: 'user',
                content: [{ type: 'audio', audio: base64 }]
            }
        };
        
        if (webSocketManager && webSocketManager.sendMessage(message)) {
            updateRealtimeMessage('📤 Sent live recording');
            
            // Request response
            setTimeout(() => {
                const responseRequest = {
                    event_id: `response_${Date.now()}`,
                    type: 'response.create'
                };
                webSocketManager.sendMessage(responseRequest);
            }, 100);
        } else {
            updateRealtimeMessage('❌ Failed to send recording - not connected');
        }
    }
}

// Create global instance
const recordingManager = new RecordingManager();

// Export functions for global access (maintain compatibility with HTML)
window.startRecording = recordingManager.start;
window.stopRecording = recordingManager.stop;
window.startRealtimeRecording = recordingManager.startRealtime;
window.stopRealtimeRecording = recordingManager.stopRealtime; 