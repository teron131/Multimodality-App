/**
 * Screen Sharing Module
 * Handles real-time screen capture and AI analysis
 */

class ScreenSharingManager {
    constructor() {
        // WebSocket connection
        this.videoStreamSocket = null;
        this.isVideoStreamConnected = false;
        
        // Screen capture elements
        this.screenStream = null;
        this.screenVideo = null;
        this.screenCanvas = null;
        this.screenContext = null;
        
        // Analysis state
        this.frameIntervalId = null;
        this.frameCounter = 0;
        this.lastFrameChecksum = null;
        
        // Bind methods to maintain context
        this.startScreenShare = this.startScreenShare.bind(this);
        this.stopScreenShare = this.stopScreenShare.bind(this);
        this.connectToVideoStream = this.connectToVideoStream.bind(this);
        this.startFrameAnalysis = this.startFrameAnalysis.bind(this);
        this.captureAndAnalyzeFrame = this.captureAndAnalyzeFrame.bind(this);
        this.testFrameCapture = this.testFrameCapture.bind(this);
    }

    async startScreenShare() {
        try {
            // Check if getDisplayMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
                throw new Error('Screen sharing not supported in this browser. Please use Chrome, Firefox, or Edge.');
            }

            // Check if we're on HTTPS (required by most browsers for screen sharing)
            if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
                updateRealtimeMessage('⚠️ Warning: Screen sharing may require HTTPS. If this fails, try accessing via https://');
            }

            updateRealtimeMessage('🖥️ Requesting screen sharing permission...');
            
            // Request screen sharing permission with optimized settings
            this.screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    width: { ideal: 1280, max: 1920 },  // Optimized: 1280p is good balance
                    height: { ideal: 720, max: 1080 },   // Optimized: 720p reduces data while maintaining quality
                    frameRate: { ideal: 5, max: 8 }     // Optimized: Lower framerate for analysis (not real-time video)
                },
                audio: false
            });

            updateRealtimeMessage('✅ Screen sharing permission granted');

            // Connect to video streaming WebSocket
            if (!this.videoStreamSocket) {
                await this.connectToVideoStream();
            }

            // Set up video element for screen capture
            this.screenVideo = document.createElement('video');
            this.screenVideo.srcObject = this.screenStream;
            this.screenVideo.autoplay = true;
            this.screenVideo.muted = true;
            this.screenVideo.playsInline = true;
            
            // Optimized video preview - smaller and less intrusive
            this.screenVideo.style.position = 'fixed';
            this.screenVideo.style.bottom = '10px';
            this.screenVideo.style.right = '10px';
            this.screenVideo.style.width = '160px';     // Smaller preview
            this.screenVideo.style.height = '90px';     // Maintains 16:9 aspect ratio
            this.screenVideo.style.border = '1px solid #4299e1';
            this.screenVideo.style.borderRadius = '6px';
            this.screenVideo.style.zIndex = '9999';
            this.screenVideo.style.backgroundColor = '#000';
            this.screenVideo.style.opacity = '0.8';     // Semi-transparent
            this.screenVideo.style.cursor = 'pointer';
            document.body.appendChild(this.screenVideo);

            // Set up canvas for frame extraction
            this.screenCanvas = document.createElement('canvas');
            this.screenContext = this.screenCanvas.getContext('2d');

            // Wait for video to be ready and playing
            this.screenVideo.onloadedmetadata = () => {
                updateRealtimeMessage(`📹 Video metadata loaded: ${this.screenVideo.videoWidth}x${this.screenVideo.videoHeight}`);
            };

            this.screenVideo.oncanplay = () => {
                updateRealtimeMessage('📹 Video can start playing');
            };

            this.screenVideo.onplaying = () => {
                // Optimize canvas size for AI analysis (max 1280x720 for efficiency)
                const maxWidth = 1280;
                const maxHeight = 720;
                const aspectRatio = this.screenVideo.videoWidth / this.screenVideo.videoHeight;
                
                if (this.screenVideo.videoWidth > maxWidth || this.screenVideo.videoHeight > maxHeight) {
                    if (aspectRatio > maxWidth / maxHeight) {
                        this.screenCanvas.width = maxWidth;
                        this.screenCanvas.height = Math.round(maxWidth / aspectRatio);
                    } else {
                        this.screenCanvas.height = maxHeight;
                        this.screenCanvas.width = Math.round(maxHeight * aspectRatio);
                    }
                } else {
                    this.screenCanvas.width = this.screenVideo.videoWidth;
                    this.screenCanvas.height = this.screenVideo.videoHeight;
                }
                
                this.updateVideoStreamStatus('Screen sharing active', 'status-ready');
                updateRealtimeMessage(`✅ Screen sharing active - Video: ${this.screenVideo.videoWidth}x${this.screenVideo.videoHeight} → Canvas: ${this.screenCanvas.width}x${this.screenCanvas.height}`);
                
                // Wait a bit more before starting frame analysis to ensure video is stable
                setTimeout(() => {
                    this.startFrameAnalysis();
                }, 1000);
                
                document.getElementById('videoStreamBtn').disabled = true;
                document.getElementById('videoDisconnectBtn').disabled = false;
            };

            // Force play the video (some browsers need this)
            this.screenVideo.play().catch(e => {
                updateRealtimeMessage(`❌ Video play error: ${e.message}`);
            });

            // Handle screen share end (user clicks browser's stop sharing)
            this.screenStream.getVideoTracks()[0].onended = () => {
                this.stopScreenShare();
            };

        } catch (error) {
            let errorMessage = error.message;
            let helpText = '';

            // Provide specific help based on the error type
            if (error.name === 'NotAllowedError') {
                errorMessage = 'Screen sharing permission denied';
                helpText = '💡 Please click "Share screen" and select a screen/window to share';
            } else if (error.name === 'NotSupportedError') {
                errorMessage = 'Screen sharing not supported';
                helpText = '💡 Please use a modern browser (Chrome 72+, Firefox 66+, Edge 79+)';
            } else if (error.name === 'NotFoundError') {
                errorMessage = 'No screen sources available';
                helpText = '💡 Make sure you have windows or screens available to share';
            } else if (error.name === 'AbortError') {
                errorMessage = 'Screen sharing was cancelled';
                helpText = '💡 You can try again by clicking "Share Screen"';
            } else if (errorMessage.includes('https')) {
                helpText = '💡 Try accessing the app via HTTPS or use localhost';
            }

            updateRealtimeMessage(`❌ Screen sharing error: ${errorMessage}`);
            if (helpText) {
                updateRealtimeMessage(helpText);
            }
            
            this.updateVideoStreamStatus('Screen sharing failed', 'status-processing');
            
            // Reset button states
            document.getElementById('videoStreamBtn').disabled = false;
            document.getElementById('videoDisconnectBtn').disabled = true;
        }
    }

    async connectToVideoStream() {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://${window.location.host}/ws/realtime/video`;
            updateRealtimeMessage(`🔗 Connecting to video analysis server: ${wsUrl}`);
            
            this.videoStreamSocket = new WebSocket(wsUrl);
            
            // Set a timeout for connection
            const connectionTimeout = setTimeout(() => {
                if (this.videoStreamSocket.readyState !== WebSocket.OPEN) {
                    updateRealtimeMessage('❌ Video server connection timeout');
                    updateRealtimeMessage('💡 Note: Video analysis requires a separate WebSocket endpoint');
                    this.videoStreamSocket.close();
                    reject(new Error('Connection timeout'));
                }
            }, 10000); // 10 second timeout
            
            this.videoStreamSocket.onopen = (event) => {
                clearTimeout(connectionTimeout);
                this.isVideoStreamConnected = true;
                updateRealtimeMessage('✅ Connected to video analysis server');
                resolve();
            };
            
            this.videoStreamSocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'video_stream.connected') {
                    updateRealtimeMessage(`🖥️ Screen analysis ready`);
                } else if (message.type === 'video_frame.analyzed') {
                    updateRealtimeMessage(`🖥️ Screen frame ${message.frame_id} analyzed`);
                    updateOutput(`🖥️ Screen Analysis: ${message.analysis}\n`);
                } else if (message.type === 'error') {
                    updateRealtimeMessage(`❌ Analysis error: ${message.message}`);
                }
            };
            
            this.videoStreamSocket.onclose = (event) => {
                clearTimeout(connectionTimeout);
                this.isVideoStreamConnected = false;
                this.videoStreamSocket = null;
                updateRealtimeMessage('🔌 Video analysis server disconnected');
            };
            
            this.videoStreamSocket.onerror = (error) => {
                clearTimeout(connectionTimeout);
                updateRealtimeMessage('❌ Connection to video analysis server failed');
                updateRealtimeMessage('💡 Screen sharing will work but without AI analysis');
                // Don't reject - allow screen sharing to work without analysis
                resolve();
            };
        });
    }

    startFrameAnalysis() {
        const interval = parseInt(document.getElementById('frameInterval').value);
        
        this.frameIntervalId = setInterval(() => {
            this.captureAndAnalyzeFrame();
        }, interval);
        
        updateRealtimeMessage(`🖥️ Frame analysis started (every ${interval/1000} seconds)`);
    }

    captureAndAnalyzeFrame() {
        if (!this.screenVideo || !this.screenCanvas || !this.screenContext || !this.isVideoStreamConnected) {
            updateRealtimeMessage('❌ Frame capture skipped - components not ready');
            return;
        }

        // Check if video is actually playing
        if (this.screenVideo.paused || this.screenVideo.ended || this.screenVideo.readyState < 2) {
            updateRealtimeMessage(`❌ Video not ready: paused=${this.screenVideo.paused}, ended=${this.screenVideo.ended}, readyState=${this.screenVideo.readyState}`);
            return;
        }

        try {
            // Clear canvas first
            this.screenContext.clearRect(0, 0, this.screenCanvas.width, this.screenCanvas.height);
            
            // Draw current video frame to canvas
            this.screenContext.drawImage(this.screenVideo, 0, 0, this.screenCanvas.width, this.screenCanvas.height);
            
            // Check if we actually drew something and detect changes
            const sampleSize = Math.min(100, this.screenCanvas.width, this.screenCanvas.height);
            const imageData = this.screenContext.getImageData(0, 0, sampleSize, sampleSize);
            const pixels = imageData.data;
            let hasContent = false;
            let checksum = 0;
            
            // Check if there are non-black pixels and calculate simple checksum
            for (let i = 0; i < pixels.length; i += 4) {
                const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
                if (r > 0 || g > 0 || b > 0) {
                    hasContent = true;
                }
                // Simple checksum for change detection (sample every 16th pixel)
                if (i % 64 === 0) {
                    checksum += r + g + b;
                }
            }
            
            if (!hasContent) {
                updateRealtimeMessage(`❌ Captured frame appears to be black - video may not be ready`);
                return;
            }
            
            // Skip analysis if frame hasn't changed significantly (percentage-based)
            if (this.lastFrameChecksum !== null && this.lastFrameChecksum > 0) {
                const changeThreshold = parseFloat(document.getElementById('changeThreshold').value);
                
                // If threshold is 0, change detection is disabled
                if (changeThreshold > 0) {
                    const changePercentage = Math.abs(checksum - this.lastFrameChecksum) / this.lastFrameChecksum;
                    const thresholdDecimal = changeThreshold / 100;
                    
                    if (changePercentage < thresholdDecimal) {
                        updateRealtimeMessage(`⏭️ Frame ${this.frameCounter + 1} skipped - change: ${(changePercentage * 100).toFixed(1)}% (< ${changeThreshold}% threshold)`);
                        return;
                    } else {
                        updateRealtimeMessage(`📸 Frame ${this.frameCounter + 1} - change: ${(changePercentage * 100).toFixed(1)}% (≥ ${changeThreshold}% threshold)`);
                    }
                } else {
                    updateRealtimeMessage(`📸 Frame ${this.frameCounter + 1} - change detection disabled`);
                }
            }
            this.lastFrameChecksum = checksum;
            
            // Convert canvas to blob with optimized compression
            this.screenCanvas.toBlob(async (blob) => {
                if (blob && blob.size > 1000) { // Ensure we have a reasonable blob size
                    this.frameCounter++;
                    const arrayBuffer = await blob.arrayBuffer();
                    const prompt = document.getElementById('screenAnalysisPrompt').value || 'Describe what you see on the screen';
                    
                    // Calculate compression ratio for monitoring
                    const compressionRatio = ((this.screenCanvas.width * this.screenCanvas.height * 3) / blob.size).toFixed(1);
                    updateRealtimeMessage(`📸 Frame ${this.frameCounter} (${(blob.size/1024).toFixed(1)}KB, ${compressionRatio}x compressed) - analyzing...`);
                    await this.sendVideoFrame(arrayBuffer, this.frameCounter, prompt);
                } else {
                    updateRealtimeMessage(`❌ Invalid blob: size=${blob ? blob.size : 'null'} bytes`);
                }
            }, 'image/jpeg', parseFloat(document.getElementById('imageQuality').value));  // User-configurable quality
            
        } catch (error) {
            updateRealtimeMessage(`❌ Frame capture error: ${error.message}`);
            console.error('Frame capture error:', error);
        }
    }

    stopScreenShare() {
        // Stop frame analysis
        if (this.frameIntervalId) {
            clearInterval(this.frameIntervalId);
            this.frameIntervalId = null;
        }

        // Stop screen stream
        if (this.screenStream) {
            this.screenStream.getTracks().forEach(track => track.stop());
            this.screenStream = null;
        }

        // Clean up video element
        if (this.screenVideo) {
            this.screenVideo.remove();
            this.screenVideo = null;
        }

        // Clean up canvas
        this.screenCanvas = null;
        this.screenContext = null;

        // Close WebSocket
        if (this.videoStreamSocket) {
            this.videoStreamSocket.close();
        }

        // Reset UI
        this.isVideoStreamConnected = false;
        this.frameCounter = 0;
        this.lastFrameChecksum = null;
        this.updateVideoStreamStatus('Screen sharing stopped', 'status-processing');
        updateRealtimeMessage('⏹️ Screen sharing stopped');
        
        document.getElementById('videoStreamBtn').disabled = false;
        document.getElementById('videoDisconnectBtn').disabled = true;
    }

    updateVideoStreamStatus(text, statusClass) {
        const statusDiv = document.getElementById('videoStreamStatus');
        if (statusDiv) {
            statusDiv.textContent = text;
            statusDiv.className = `status-indicator ${statusClass}`;
            statusDiv.style.display = 'block';
        }
    }

    testFrameCapture() {
        // Check which components are missing
        const missing = [];
        if (!this.screenVideo) missing.push('video element');
        if (!this.screenCanvas) missing.push('canvas element');
        if (!this.screenContext) missing.push('canvas context');
        
        if (missing.length > 0) {
            updateRealtimeMessage(`❌ Test failed - missing: ${missing.join(', ')}`);
            updateRealtimeMessage('💡 Please start screen sharing first before testing frame capture');
            return;
        }

        // Check if screen sharing is active
        if (!this.screenStream || this.screenStream.getVideoTracks().length === 0) {
            updateRealtimeMessage('❌ Test failed - no active screen stream');
            updateRealtimeMessage('💡 Please start screen sharing first');
            return;
        }

        updateRealtimeMessage(`🧪 Testing frame capture...`);
        updateRealtimeMessage(`📹 Video state: playing=${!this.screenVideo.paused}, ended=${this.screenVideo.ended}, readyState=${this.screenVideo.readyState}`);
        updateRealtimeMessage(`📹 Video dimensions: ${this.screenVideo.videoWidth}x${this.screenVideo.videoHeight}`);
        updateRealtimeMessage(`📹 Canvas dimensions: ${this.screenCanvas.width}x${this.screenCanvas.height}`);

        try {
            // Clear canvas and draw frame
            this.screenContext.clearRect(0, 0, this.screenCanvas.width, this.screenCanvas.height);
            this.screenContext.drawImage(this.screenVideo, 0, 0, this.screenCanvas.width, this.screenCanvas.height);

            // Sample some pixels
            const centerX = Math.floor(this.screenCanvas.width / 2);
            const centerY = Math.floor(this.screenCanvas.height / 2);
            const centerPixel = this.screenContext.getImageData(centerX, centerY, 1, 1).data;
            updateRealtimeMessage(`🔍 Center pixel: R=${centerPixel[0]}, G=${centerPixel[1]}, B=${centerPixel[2]}, A=${centerPixel[3]}`);

            // Create a small test image to verify the canvas works
            const testCanvas = document.createElement('canvas');
            testCanvas.width = 200;
            testCanvas.height = 200;
            const testCtx = testCanvas.getContext('2d');
            
            // Draw the captured frame scaled down
            testCtx.drawImage(this.screenCanvas, 0, 0, 200, 200);
            
            // Create a data URL for visual inspection
            const dataUrl = testCanvas.toDataURL('image/jpeg', 0.9);
            updateRealtimeMessage(`📊 Test image data URL length: ${dataUrl.length} chars`);
            
            // Show if the data URL contains actual image data (not just a black image)
            if (dataUrl.length > 5000) {
                updateRealtimeMessage(`✅ Test capture appears to contain image data`);
            } else {
                updateRealtimeMessage(`❌ Test capture appears to be empty/black`);
            }

        } catch (error) {
            updateRealtimeMessage(`❌ Test error: ${error.message}`);
            console.error('Test capture error:', error);
        }
    }

    // Send video to streaming endpoint
    async sendVideoToStream(videoFile, prompt = 'Analyze this video') {
        if (!this.isVideoStreamConnected || !this.videoStreamSocket) {
            updateRealtimeMessage('❌ Video stream not connected');
            return;
        }
        
        try {
            const arrayBuffer = await videoFile.arrayBuffer();
            const base64 = this.arrayBufferToBase64(arrayBuffer);
            
            const message = {
                type: 'video_complete',
                video: base64,
                prompt: prompt,
                timestamp: Date.now()
            };
            
            this.videoStreamSocket.send(JSON.stringify(message));
            updateRealtimeMessage(`📤 Video sent to streaming endpoint: ${videoFile.name}`);
        } catch (error) {
            updateRealtimeMessage(`❌ Failed to send video to stream: ${error.message}`);
        }
    }

    // Send individual video frame
    async sendVideoFrame(frameData, frameId, prompt = 'Describe this video frame') {
        if (!this.isVideoStreamConnected || !this.videoStreamSocket) {
            updateRealtimeMessage('❌ Video stream not connected');
            return;
        }
        
        try {
            const base64 = this.arrayBufferToBase64(frameData);
            
            const message = {
                type: 'video_frame',
                frame: base64,
                frame_id: frameId,
                prompt: prompt,
                timestamp: Date.now()
            };
            
            this.videoStreamSocket.send(JSON.stringify(message));
            updateRealtimeMessage(`📤 Video frame ${frameId} sent for analysis`);
        } catch (error) {
            updateRealtimeMessage(`❌ Failed to send video frame: ${error.message}`);
        }
    }

    // Test screen sharing support and provide diagnostics
    testScreenShareSupport() {
        updateRealtimeMessage('🔍 Testing screen sharing support...');
        
        // Check browser support
        if (!navigator.mediaDevices) {
            updateRealtimeMessage('❌ MediaDevices API not available');
            return;
        }
        
        if (!navigator.mediaDevices.getDisplayMedia) {
            updateRealtimeMessage('❌ getDisplayMedia not supported');
            updateRealtimeMessage('💡 Please use a modern browser (Chrome 72+, Firefox 66+, Edge 79+)');
            return;
        }
        
        updateRealtimeMessage('✅ getDisplayMedia API available');
        
        // Check protocol
        const protocol = location.protocol;
        const hostname = location.hostname;
        updateRealtimeMessage(`🌐 Protocol: ${protocol}, Host: ${hostname}`);
        
        if (protocol === 'https:') {
            updateRealtimeMessage('✅ HTTPS - Screen sharing should work');
        } else if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') {
            updateRealtimeMessage('✅ Localhost - Screen sharing should work');
        } else {
            updateRealtimeMessage('⚠️ HTTP on non-localhost - may require HTTPS');
            updateRealtimeMessage('💡 Try accessing via https:// if screen sharing fails');
        }
        
        // Check permissions API if available
        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({name: 'display-capture'}).then(result => {
                updateRealtimeMessage(`🔐 Display capture permission: ${result.state}`);
                if (result.state === 'denied') {
                    updateRealtimeMessage('💡 Screen sharing permission denied - please reset in browser settings');
                }
            }).catch(err => {
                updateRealtimeMessage('🔐 Could not check display capture permissions');
            });
        }
        
        // Test basic canvas support
        try {
            const testCanvas = document.createElement('canvas');
            const testCtx = testCanvas.getContext('2d');
            if (testCanvas && testCtx) {
                updateRealtimeMessage('✅ Canvas API available');
            } else {
                updateRealtimeMessage('❌ Canvas API not available');
            }
        } catch (error) {
            updateRealtimeMessage(`❌ Canvas test failed: ${error.message}`);
        }
        
        // Test WebSocket support
        try {
            const testWs = new WebSocket(`ws://${window.location.host}/ws/realtime`);
            testWs.onopen = () => {
                updateRealtimeMessage('✅ WebSocket connection works');
                testWs.close();
            };
            testWs.onerror = () => {
                updateRealtimeMessage('❌ WebSocket connection failed');
            };
        } catch (error) {
            updateRealtimeMessage(`❌ WebSocket test failed: ${error.message}`);
        }
        
        updateRealtimeMessage('🔍 Support check complete');
    }

    // Helper function for efficient base64 conversion
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        const chunkSize = 8192; // Process in chunks to avoid stack overflow
        
        for (let i = 0; i < bytes.length; i += chunkSize) {
            const chunk = bytes.slice(i, i + chunkSize);
            binary += String.fromCharCode.apply(null, chunk);
        }
        
        return btoa(binary);
    }
}

// Create global instance
const screenSharingManager = new ScreenSharingManager();

// Export functions for global access (maintain compatibility with HTML)
window.startScreenShare = screenSharingManager.startScreenShare;
window.stopScreenShare = screenSharingManager.stopScreenShare;
window.testFrameCapture = screenSharingManager.testFrameCapture;
window.testScreenShareSupport = screenSharingManager.testScreenShareSupport; 