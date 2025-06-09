#!/usr/bin/env python3
"""
AudioInsight-CPP Test Script for Ultravox Integration

This script tests the llama-server API with audio files to evaluate
the Ultravox model's performance for audio transcription and analysis.
"""

import argparse
import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltravoxTester:
    """Test client for Ultravox model via llama-server API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8081"):
        self.base_url = base_url
        self.session = requests.Session()

    def check_health(self) -> bool:
        """Check if the llama-server is running and healthy."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ Server is healthy: {response.json()}")
                return True
            else:
                logger.error(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to server: {e}")
            return False

    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the loaded model."""
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=10)
            if response.status_code == 200:
                models = response.json()
                logger.info(f"📋 Available models: {json.dumps(models, indent=2)}")
                return models
            else:
                logger.warning(f"⚠️ Could not get model info: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"⚠️ Model info request failed: {e}")
            return None

    def test_multimodal_approaches(self, audio_path: Path, prompt: str = None) -> Dict[str, Any]:
        """
        Test different approaches to send audio to the multimodal model.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"🧪 Testing multimodal approaches for: {audio_path}")

        if prompt is None:
            prompt = "Please transcribe this audio and provide analysis including transcript, speaker info, topics, and sentiment."

        results = {}

        # Approach 1: Multimodal JSON with base64 audio
        logger.info("🔄 Testing Approach 1: Multimodal JSON with base64...")
        try:
            import base64

            with open(audio_path, "rb") as f:
                audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            multimodal_data = {"model": "ultravox", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "audio", "audio": {"data": audio_base64, "format": "wav"}}]}], "temperature": 0.1, "max_tokens": 500}

            start_time = time.time()
            response = self.session.post(f"{self.base_url}/v1/chat/completions", json=multimodal_data, timeout=60)
            processing_time = time.time() - start_time

            results["multimodal_json"] = {"status_code": response.status_code, "processing_time": processing_time, "response_preview": response.text[:300] + "..." if len(response.text) > 300 else response.text, "success": response.status_code == 200}

            if response.status_code == 200:
                results["multimodal_json"]["response"] = response.json()

        except Exception as e:
            results["multimodal_json"] = {"error": str(e), "success": False}

        # Approach 2: FormData with audio file
        logger.info("🔄 Testing Approach 2: FormData with audio file...")
        try:
            files = {"audio": (audio_path.name, open(audio_path, "rb"), "audio/wav")}
            data = {"prompt": prompt, "temperature": 0.1, "max_tokens": 500}

            start_time = time.time()
            response = self.session.post(f"{self.base_url}/v1/chat/completions", files=files, data=data, timeout=60)
            processing_time = time.time() - start_time

            results["formdata"] = {"status_code": response.status_code, "processing_time": processing_time, "response_preview": response.text[:300] + "..." if len(response.text) > 300 else response.text, "success": response.status_code == 200}

            if response.status_code == 200:
                results["formdata"]["response"] = response.json()

            files["audio"][1].close()

        except Exception as e:
            results["formdata"] = {"error": str(e), "success": False}

        # Approach 3: Check available endpoints
        logger.info("🔄 Testing Approach 3: Check available endpoints...")
        try:
            # Test different endpoints
            endpoints_to_test = ["/v1/models", "/models", "/v1/completions", "/completion", "/v1/chat/completions"]

            results["endpoints"] = {}
            for endpoint in endpoints_to_test:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    results["endpoints"][endpoint] = {"status_code": response.status_code, "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text}
                except Exception as e:
                    results["endpoints"][endpoint] = {"error": str(e)}

        except Exception as e:
            results["endpoints"] = {"error": str(e)}

        return results

    def transcribe_audio_file(self, audio_path: Path, prompt: str = None) -> Dict[str, Any]:
        """
        Send an audio file to the Ultravox model for transcription and analysis using OpenAI format.

        Args:
            audio_path: Path to the audio file
            prompt: Custom prompt for the model

        Returns:
            Dictionary with the response and metadata
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"🎵 Processing audio file: {audio_path}")

        # Default prompt if none provided
        if prompt is None:
            prompt = "Please transcribe and analyze this audio. What is being said?"

        # Read and encode audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        # Use correct llama.cpp audio format (following llama-box documentation)
        payload = {"model": "ultravox", "temperature": 0.1, "max_tokens": 150, "messages": [{"role": "system", "content": [{"type": "text", "text": "You are a helpful assistant."}]}, {"role": "user", "content": [{"type": "input_audio", "input_audio": {"format": "wav", "data": audio_base64}}, {"type": "text", "text": prompt}]}]}

        start_time = time.time()
        logger.info(f"📤 Sending {len(audio_data)} bytes of audio data (input_audio format)...")

        try:
            response = self.session.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=60)
            processing_time = time.time() - start_time

            logger.info(f"📡 Response status: {response.status_code}")
            logger.info(f"⏱️ Processing time: {processing_time:.2f}s")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Processing completed in {processing_time:.2f}s")
                return {"success": True, "response": result, "processing_time": processing_time, "audio_file": str(audio_path)}
            else:
                logger.error(f"❌ input_audio format failed: {response.status_code}")
                logger.error(f"Response: {response.text}")

                # Try alternative format
                logger.info("🔄 Trying alternative audio format...")
                return self._try_alternative_audio_format(audio_path, audio_data, audio_base64, prompt, processing_time)

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Request exception: {e}")
            return {"success": False, "error": str(e), "processing_time": processing_time, "audio_file": str(audio_path)}

    def _try_alternative_audio_format(self, audio_path: Path, audio_data: bytes, audio_base64: str, prompt: str, initial_time: float) -> Dict[str, Any]:
        """Try alternative audio format if OpenAI format fails"""
        try:
            # Direct audio field format
            payload = {"model": "ultravox", "max_tokens": 150, "messages": [{"role": "user", "content": prompt, "audio": {"data": audio_base64, "format": "wav"}}]}

            start_time = time.time()
            response = self.session.post(f"{self.base_url}/v1/chat/completions", json=payload, timeout=60)
            processing_time = time.time() - start_time + initial_time

            logger.info(f"📡 Alt format response: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Alternative format successful!")
                return {"success": True, "response": result, "processing_time": processing_time, "audio_file": str(audio_path)}
            else:
                logger.error(f"❌ Alternative format also failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}", "processing_time": processing_time, "audio_file": str(audio_path)}

        except Exception as e:
            processing_time = time.time() - start_time + initial_time
            logger.error(f"❌ Alternative format exception: {e}")
            return {"success": False, "error": str(e), "processing_time": processing_time, "audio_file": str(audio_path)}

    def test_completion_endpoint(self, prompt: str = "Hello, how are you?") -> Dict[str, Any]:
        """Test the basic completion endpoint without audio."""
        logger.info("🧪 Testing basic completion endpoint...")

        start_time = time.time()

        try:
            response = self.session.post(f"{self.base_url}/completion", json={"prompt": prompt, "n_predict": 100, "temperature": 0.7, "stream": False}, timeout=30)

            processing_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Completion test successful in {processing_time:.2f}s")
                return {"success": True, "response": result, "processing_time": processing_time}
            else:
                logger.error(f"❌ Completion test failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}", "processing_time": processing_time}

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Completion test exception: {e}")
            return {"success": False, "error": str(e), "processing_time": processing_time}


def run_comprehensive_test(tester: UltravoxTester, audio_dir: Path) -> None:
    """Run a comprehensive test suite."""

    print("🚀 Starting AudioInsight-CPP Comprehensive Test")
    print("=" * 60)

    # 1. Health check
    print("\n1️⃣ Health Check")
    if not tester.check_health():
        print("❌ Server is not healthy. Please start llama-server first.")
        return

    # 2. Model info
    print("\n2️⃣ Model Information")
    model_info = tester.get_model_info()

    # 3. Basic completion test
    print("\n3️⃣ Basic Completion Test")
    completion_result = tester.test_completion_endpoint("Explain what you are and what you can do with audio.")
    if completion_result["success"]:
        print(f"✅ Completion: {completion_result['response'].get('content', 'No content')}")
    else:
        print(f"❌ Completion failed: {completion_result['error']}")

    # 4. Audio file tests
    print("\n4️⃣ Audio File Tests")

    # Look for audio files
    audio_files = []
    if audio_dir.exists():
        for ext in ["*.wav", "*.mp3", "*.flac", "*.m4a"]:
            audio_files.extend(audio_dir.glob(ext))

    if not audio_files:
        print(f"⚠️ No audio files found in {audio_dir}")
        print("💡 Try placing some test audio files in the audio/ directory")
    else:
        print(f"📁 Found {len(audio_files)} audio files")

        for i, audio_file in enumerate(audio_files[:3], 1):  # Test up to 3 files
            print(f"\n   📄 Test {i}: {audio_file.name}")
            result = tester.transcribe_audio_file(audio_file)

            if result["success"]:
                response = result["response"]
                if "choices" in response and response["choices"]:
                    content = response["choices"][0].get("message", {}).get("content", "No content")
                    print(f"   ✅ Result: {content[:100]}...")
                    print(f"   ⏱️ Processing time: {result['processing_time']:.2f}s")
                else:
                    print(f"   ⚠️ Unexpected response format: {response}")
            else:
                print(f"   ❌ Failed: {result['error']}")

    print("\n" + "=" * 60)
    print("🏁 Test completed!")


def main():
    parser = argparse.ArgumentParser(description="Test Ultravox integration with llama-server")
    parser.add_argument("--server", default="http://127.0.0.1:8081", help="llama-server URL (default: http://127.0.0.1:8081)")
    parser.add_argument("--audio-dir", type=Path, default=Path("../audio"), help="Directory to search for audio files (default: ../audio)")
    parser.add_argument("--audio-file", type=Path, help="Specific audio file to test")
    parser.add_argument("--prompt", help="Custom prompt for audio analysis")
    parser.add_argument("--health-only", action="store_true", help="Only check server health")

    args = parser.parse_args()

    # Initialize tester
    tester = UltravoxTester(args.server)

    if args.health_only:
        # Just check health
        if tester.check_health():
            print("✅ Server is healthy")
        else:
            print("❌ Server is not healthy")
        return

    if args.audio_file:
        # Test specific file
        print(f"🎵 Testing specific file: {args.audio_file}")
        result = tester.transcribe_audio_file(args.audio_file, args.prompt)
        print(json.dumps(result, indent=2))
    else:
        # Run comprehensive test
        run_comprehensive_test(tester, args.audio_dir)


if __name__ == "__main__":
    main()
