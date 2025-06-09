import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from multimodality_app.llm import get_response


class TestGetResponse:
    """Test suite for the get_response function."""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing."""
        with patch("multimodality_app.llm.llm") as mock:
            mock_response = AIMessage(content="Mock response from LLM")
            mock.invoke.return_value = mock_response
            yield mock

    @pytest.fixture
    def sample_image_file(self):
        """Create a temporary image file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    @pytest.fixture
    def sample_audio_file(self):
        """Create a temporary audio file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake audio data")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    def test_get_response_text_only(self, mock_llm):
        """Test get_response with text input only."""
        text_input = "Hello, how are you?"

        response = get_response(text_input=text_input)

        # Verify the LLM was called correctly
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)
        assert call_args[0].content == [{"type": "text", "text": text_input}]
        assert isinstance(response, AIMessage)

    @patch("multimodality_app.llm.encode_image")
    def test_get_response_image_only(self, mock_encode_image, mock_llm, sample_image_file):
        """Test get_response with image input only."""
        mock_encode_image.return_value = "base64_image_data"

        response = get_response(image_path=str(sample_image_file))

        # Verify encode_image was called
        mock_encode_image.assert_called_once_with(str(sample_image_file))

        # Verify the LLM was called correctly
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)
        expected_content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,base64_image_data"}}]
        assert call_args[0].content == expected_content
        assert isinstance(response, AIMessage)

    @patch("multimodality_app.llm.encode_audio")
    def test_get_response_audio_only(self, mock_encode_audio, mock_llm, sample_audio_file):
        """Test get_response with audio input only."""
        mock_encode_audio.return_value = "base64_audio_data"

        response = get_response(audio_path=str(sample_audio_file))

        # Verify encode_audio was called
        mock_encode_audio.assert_called_once_with(str(sample_audio_file))

        # Verify the LLM was called correctly
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)
        expected_content = [{"type": "input_audio", "input_audio": {"data": "base64_audio_data", "format": "mp3"}}]
        assert call_args[0].content == expected_content
        assert isinstance(response, AIMessage)

    @patch("multimodality_app.llm.encode_audio")
    @patch("multimodality_app.llm.encode_image")
    def test_get_response_multimodal(self, mock_encode_image, mock_encode_audio, mock_llm, sample_image_file, sample_audio_file):
        """Test get_response with text, image, and audio inputs."""
        mock_encode_image.return_value = "base64_image_data"
        mock_encode_audio.return_value = "base64_audio_data"

        text_input = "What do you see and hear?"

        response = get_response(text_input=text_input, image_path=str(sample_image_file), audio_path=str(sample_audio_file))

        # Verify encoding functions were called
        mock_encode_image.assert_called_once_with(str(sample_image_file))
        mock_encode_audio.assert_called_once_with(str(sample_audio_file))

        # Verify the LLM was called correctly
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)

        expected_content = [{"type": "text", "text": text_input}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,base64_image_data"}}, {"type": "input_audio", "input_audio": {"data": "base64_audio_data", "format": "mp3"}}]
        assert call_args[0].content == expected_content
        assert isinstance(response, AIMessage)

    def test_get_response_no_inputs(self, mock_llm):
        """Test get_response raises ValueError when no inputs are provided."""
        with pytest.raises(ValueError) as exc_info:
            get_response()

        assert "At least one of text_input, image_path, or audio_path must be provided" in str(exc_info.value)
        mock_llm.invoke.assert_not_called()

    def test_get_response_empty_inputs(self, mock_llm):
        """Test get_response raises ValueError when all inputs are empty/None."""
        with pytest.raises(ValueError) as exc_info:
            get_response(text_input=None, image_path=None, audio_path=None)

        assert "At least one of text_input, image_path, or audio_path must be provided" in str(exc_info.value)
        mock_llm.invoke.assert_not_called()

    @patch("multimodality_app.llm.encode_image")
    def test_get_response_image_encoding_error(self, mock_encode_image, mock_llm, sample_image_file):
        """Test get_response propagates image encoding errors."""
        mock_encode_image.side_effect = ValueError("Unsupported image format")

        with pytest.raises(ValueError) as exc_info:
            get_response(image_path=str(sample_image_file))

        assert "Unsupported image format" in str(exc_info.value)
        mock_llm.invoke.assert_not_called()

    @patch("multimodality_app.llm.encode_audio")
    def test_get_response_audio_encoding_error(self, mock_encode_audio, mock_llm, sample_audio_file):
        """Test get_response propagates audio encoding errors."""
        mock_encode_audio.side_effect = RuntimeError("FFmpeg conversion failed")

        with pytest.raises(RuntimeError) as exc_info:
            get_response(audio_path=str(sample_audio_file))

        assert "FFmpeg conversion failed" in str(exc_info.value)
        mock_llm.invoke.assert_not_called()

    def test_get_response_llm_error(self, mock_llm):
        """Test get_response propagates LLM invocation errors."""
        mock_llm.invoke.side_effect = Exception("LLM API error")

        with pytest.raises(Exception) as exc_info:
            get_response(text_input="Hello")

        assert "LLM API error" in str(exc_info.value)

    @patch("multimodality_app.llm.encode_image")
    def test_get_response_text_and_image(self, mock_encode_image, mock_llm, sample_image_file):
        """Test get_response with text and image inputs."""
        mock_encode_image.return_value = "base64_image_data"
        text_input = "Describe this image"

        response = get_response(text_input=text_input, image_path=str(sample_image_file))

        # Verify the LLM was called correctly
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)

        expected_content = [{"type": "text", "text": text_input}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,base64_image_data"}}]
        assert call_args[0].content == expected_content
        assert isinstance(response, AIMessage)

    @patch("multimodality_app.llm.encode_audio")
    def test_get_response_text_and_audio(self, mock_encode_audio, mock_llm, sample_audio_file):
        """Test get_response with text and audio inputs."""
        mock_encode_audio.return_value = "base64_audio_data"
        text_input = "Transcribe this audio"

        response = get_response(text_input=text_input, audio_path=str(sample_audio_file))

        # Verify the LLM was called correctly
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)

        expected_content = [{"type": "text", "text": text_input}, {"type": "input_audio", "input_audio": {"data": "base64_audio_data", "format": "mp3"}}]
        assert call_args[0].content == expected_content
        assert isinstance(response, AIMessage)

    def test_get_response_return_type(self, mock_llm):
        """Test that get_response returns the correct type."""
        response = get_response(text_input="Hello")

        assert isinstance(response, AIMessage)
        assert response.content == "Mock response from LLM"


class TestLLMConfiguration:
    """Test suite for LLM configuration."""

    def test_llm_exists(self):
        """Test that LLM instance is created."""
        from multimodality_app.llm import llm

        assert llm is not None
        # The LLM should be a ChatOpenAI instance
        assert hasattr(llm, "invoke")
        # Check for either model or model_name attribute
        assert hasattr(llm, "model") or hasattr(llm, "model_name")
        # Check for either api_key
        assert hasattr(llm, "api_key")

    def test_get_response_function_exists(self):
        """Test that get_response function is properly imported and callable."""
        from multimodality_app.llm import get_response

        assert callable(get_response)
        # Check function signature
        import inspect

        sig = inspect.signature(get_response)
        expected_params = {"text_input", "image_path", "audio_path"}
        actual_params = set(sig.parameters.keys())
        assert expected_params == actual_params
