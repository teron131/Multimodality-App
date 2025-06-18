/**
 * Utilities Module
 * Common functions for UI management, progress handling, and message utilities
 */

class Utils {
    constructor() {
        // Bind methods to maintain context
        this.updateOutput = this.updateOutput.bind(this);
        this.updateRealtimeMessage = this.updateRealtimeMessage.bind(this);
        this.sanitizeDisplayMessage = this.sanitizeDisplayMessage.bind(this);
        this.showProgress = this.showProgress.bind(this);
        this.hideProgress = this.hideProgress.bind(this);
        this.arrayBufferToBase64 = this.arrayBufferToBase64.bind(this);
        this.switchTab = this.switchTab.bind(this);
        this.formatFileSize = this.formatFileSize.bind(this);
        this.formatDuration = this.formatDuration.bind(this);
    }

    updateOutput(text, clear = false) {
        const outputElement = document.getElementById('output');
        if (!outputElement) return;
        
        if (clear) {
            outputElement.textContent = text;
        } else {
            outputElement.textContent += text;
        }
        
        // Auto-scroll to bottom
        outputElement.scrollTop = outputElement.scrollHeight;
    }

    updateRealtimeMessage(message) {
        const messagesDiv = document.getElementById('realtimeMessages');
        if (!messagesDiv) return;
        
        // Sanitize message to avoid displaying long binary data
        const sanitizedMessage = this.sanitizeDisplayMessage(message);
        const timestamp = new Date().toLocaleTimeString();
        messagesDiv.textContent += `[${timestamp}] ${sanitizedMessage}\n`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    sanitizeDisplayMessage(message) {
        // Simple sanitization for user-friendly messages
        if (typeof message === 'string') {
            if (message.length > 500) {
                // Truncate very long strings
                return message.substring(0, 500) + `... <message truncated>`;
            }
            return message;
        }
        
        return String(message);
    }

    showProgress() {
        const progressElement = document.getElementById('progressIndicator');
        if (progressElement) {
            progressElement.style.display = 'block';
        }
    }

    hideProgress() {
        const progressElement = document.getElementById('progressIndicator');
        if (progressElement) {
            progressElement.style.display = 'none';
        }
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

    switchTab(tabName) {
        // Hide all tab contents
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
        });
        
        // Remove active class from all tabs
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Show selected tab content
        const selectedContent = document.getElementById(tabName);
        if (selectedContent) {
            selectedContent.classList.add('active');
        }
        
        // Activate selected tab
        const selectedTab = document.querySelector(`.tab[onclick*="${tabName}"]`);
        if (selectedTab) {
            selectedTab.classList.add('active');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Theme management
    toggleTheme() {
        const body = document.body;
        const currentTheme = body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);
    }

    // Clipboard utilities
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.updateRealtimeMessage('✅ Copied to clipboard');
        } catch (error) {
            this.updateRealtimeMessage('❌ Failed to copy to clipboard');
        }
    }

    // URL utilities
    downloadAsFile(content, filename, contentType = 'text/plain') {
        const blob = new Blob([content], { type: contentType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // Input validation utilities
    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    validateURL(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    // Error handling utilities
    handleError(error, context = '') {
        console.error(`Error in ${context}:`, error);
        const message = error.message || 'An unexpected error occurred';
        this.updateOutput(`❌ Error ${context}: ${message}\n`);
        this.updateRealtimeMessage(`❌ Error ${context}: ${message}`);
    }

    // Performance monitoring
    startTimer(label) {
        console.time(label);
    }

    endTimer(label) {
        console.timeEnd(label);
    }

    // Local storage utilities
    saveToStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
            return false;
        }
    }

    loadFromStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to load from localStorage:', error);
            return defaultValue;
        }
    }
}

// Create global instance
const utils = new Utils();

// Export functions for global access (maintain compatibility with HTML)
window.updateOutput = utils.updateOutput;
window.updateRealtimeMessage = utils.updateRealtimeMessage;
window.sanitizeDisplayMessage = utils.sanitizeDisplayMessage;
window.showProgress = utils.showProgress;
window.hideProgress = utils.hideProgress;
window.arrayBufferToBase64 = utils.arrayBufferToBase64;
window.switchTab = utils.switchTab;

// Initialize theme on load
document.addEventListener('DOMContentLoaded', () => {
    utils.initializeTheme();
}); 