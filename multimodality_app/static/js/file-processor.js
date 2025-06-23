/**
 * File Processor
 * Handles file upload and processing for different media types
 */

class FileProcessor {
    constructor() {
        // Bind methods to maintain context
        this.processText = this.processText.bind(this);
        this.processAudio = this.processAudio.bind(this);
        this.processImage = this.processImage.bind(this);
        this.processVideo = this.processVideo.bind(this);
        this.processMultimodal = this.processMultimodal.bind(this);
    }

    async processText() {
        const textInput = document.getElementById('textInput');
        if (!textInput) {
            updateOutput('❌ Text input not found.');
            return;
        }

        const text = textInput.value;
        if (!text.trim()) {
            updateOutput('❌ Please enter some text to analyze.');
            return;
        }

        updateOutput('📝 Processing text input...', true);
        showProgress();

        try {
            // Using the LLM directly via a simple endpoint
            const response = await fetch('/api/invoke-text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    prompt: 'Analyze this text and provide insights.'
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Unable to process text. Please try again.`);
            }

            const result = await response.json();
            updateOutput(`✅ Text Analysis Complete:\n${result.analysis || result.message}\n`);
        } catch (error) {
            updateOutput(`❌ Text Processing Error: ${error.message}\n`);
        } finally {
            hideProgress();
        }
    }

    async processAudio() {
        const fileInput = document.getElementById('audioFile');
        const promptInput = document.getElementById('audioPrompt');
        
        if (!fileInput || !fileInput.files[0]) {
            updateOutput('❌ Please select an audio file.');
            return;
        }

        const file = fileInput.files[0];
        const prompt = promptInput ? promptInput.value : 'Please transcribe this audio.';
        
        updateOutput('🎵 Processing audio file...', true);
        showProgress();

        try {
            const formData = new FormData();
            formData.append('audio', file);
            formData.append('prompt', prompt);

            const response = await fetch('/api/invoke-audio', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Unable to process audio file. Please check the file format and try again.`);
            }

            const result = await response.json();
            updateOutput(`✅ Audio Processing Complete:\n${result.transcription}\n`);
        } catch (error) {
            updateOutput(`❌ Audio Processing Error: ${error.message}\n`);
        } finally {
            hideProgress();
        }
    }

    async processImage() {
        const fileInput = document.getElementById('imageFile');
        const promptInput = document.getElementById('imagePrompt');
        
        if (!fileInput || !fileInput.files[0]) {
            updateOutput('❌ Please select an image file.');
            return;
        }

        const file = fileInput.files[0];
        const prompt = promptInput ? promptInput.value : 'Please analyze this image.';
        
        updateOutput('🖼️ Processing image file...', true);
        showProgress();

        try {
            const formData = new FormData();
            formData.append('image', file);
            formData.append('prompt', prompt);

            const response = await fetch('/api/invoke-image', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Unable to process image file. Please check the file format and try again.`);
            }

            const result = await response.json();
            updateOutput(`✅ Image Processing Complete:\n${result.analysis}\n`);
        } catch (error) {
            updateOutput(`❌ Image Processing Error: ${error.message}\n`);
        } finally {
            hideProgress();
        }
    }

    async processVideo() {
        const fileInput = document.getElementById('videoFile');
        const promptInput = document.getElementById('videoPrompt');
        
        if (!fileInput || !fileInput.files[0]) {
            updateOutput('❌ Please select a video file.');
            return;
        }

        const file = fileInput.files[0];
        const prompt = promptInput ? promptInput.value : 'Please analyze this video.';
        
        updateOutput('🎬 Processing video file...', true);
        showProgress();

        try {
            const formData = new FormData();
            formData.append('video', file);
            formData.append('prompt', prompt);

            const response = await fetch('/api/invoke-video', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Unable to process video file. Please check the file format and try again.`);
            }

            const result = await response.json();
            updateOutput(`✅ Video Processing Complete:\n${result.analysis}\n`);
        } catch (error) {
            updateOutput(`❌ Video Processing Error: ${error.message}\n`);
        } finally {
            hideProgress();
        }
    }

    async processMultimodal() {
        const audioInput = document.getElementById('multiAudio');
        const imageInput = document.getElementById('multiImage');
        const promptInput = document.getElementById('multiPrompt');
        
        if (!audioInput?.files[0] && !imageInput?.files[0]) {
            updateOutput('❌ Please select at least one file (audio or image).');
            return;
        }

        const prompt = promptInput ? promptInput.value : 'Please analyze this multimodal content.';
        
        updateOutput('🔗 Processing multimodal content...', true);
        showProgress();

        try {
            const formData = new FormData();
            if (audioInput?.files[0]) {
                formData.append('audio', audioInput.files[0]);
            }
            if (imageInput?.files[0]) {
                formData.append('image', imageInput.files[0]);
            }
            formData.append('prompt', prompt);

            const response = await fetch('/api/invoke-multimodal', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Unable to process files. Please check the file formats and try again.`);
            }

            const result = await response.json();
            updateOutput(`✅ Multimodal Processing Complete:\n${result.analysis}\n`);
        } catch (error) {
            updateOutput(`❌ Multimodal Processing Error: ${error.message}\n`);
        } finally {
            hideProgress();
        }
    }

    // File validation utilities
    validateAudioFile(file) {
        const allowedTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/webm', 'audio/ogg'];
        const maxSize = 100 * 1024 * 1024; // 100MB
        
        if (!allowedTypes.includes(file.type)) {
            throw new Error('Invalid audio file type. Please use WAV, MP3, WebM, or OGG format.');
        }
        
        if (file.size > maxSize) {
            throw new Error('Audio file too large. Please use a file smaller than 100MB.');
        }
        
        return true;
    }

    validateImageFile(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
        const maxSize = 50 * 1024 * 1024; // 50MB
        
        if (!allowedTypes.includes(file.type)) {
            throw new Error('Invalid image file type. Please use JPEG, PNG, GIF, or WebP format.');
        }
        
        if (file.size > maxSize) {
            throw new Error('Image file too large. Please use a file smaller than 50MB.');
        }
        
        return true;
    }

    validateVideoFile(file) {
        const allowedTypes = ['video/mp4', 'video/webm', 'video/ogg', 'video/avi', 'video/mov'];
        const maxSize = 500 * 1024 * 1024; // 500MB
        
        if (!allowedTypes.includes(file.type)) {
            throw new Error('Invalid video file type. Please use MP4, WebM, OGG, AVI, or MOV format.');
        }
        
        if (file.size > maxSize) {
            throw new Error('Video file too large. Please use a file smaller than 500MB.');
        }
        
        return true;
    }
}

// Create global instance
const fileProcessor = new FileProcessor();

// Export functions for global access (maintain compatibility with HTML)
window.processText = fileProcessor.processText;
window.processAudio = fileProcessor.processAudio;
window.processImage = fileProcessor.processImage;
window.processVideo = fileProcessor.processVideo;
window.processMultimodal = fileProcessor.processMultimodal; 