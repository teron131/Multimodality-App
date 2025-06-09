import base64
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from multimodality_app.utils import (
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_IMAGE_FORMATS,
    encode_audio,
    encode_image,
)


class TestEncodeImage:
    """Test suite for the encode_image function."""

    @pytest.fixture
    def sample_image_path(self) -> Path:
        """Path to a sample image for testing."""
        return Path(__file__).parent.parent / "image" / "150920049.png"

    def test_encode_image_success(self, sample_image_path: Path) -> None:
        """Test successful image encoding with a real image file."""
        if not sample_image_path.exists():
            pytest.skip(f"Sample image not found: {sample_image_path}")

        result = encode_image(sample_image_path)

        # Verify it's a valid base64 string
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify we can decode it back to bytes
        decoded_data = base64.b64decode(result)
        assert len(decoded_data) > 0

        # Verify the decoded data matches the original file
        with open(sample_image_path, "rb") as f:
            original_data = f.read()
        assert decoded_data == original_data

    def test_encode_image_with_string_path(self, sample_image_path: Path) -> None:
        """Test that string paths work as well as Path objects."""
        if not sample_image_path.exists():
            pytest.skip(f"Sample image not found: {sample_image_path}")

        result = encode_image(str(sample_image_path))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_image_unsupported_format(self) -> None:
        """Test error handling for unsupported image formats."""
        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
            test_file = Path(f.name)
            f.write(b"fake image data")

        try:
            with pytest.raises(ValueError) as exc_info:
                encode_image(test_file)

            assert "Unsupported image format" in str(exc_info.value)
            assert ".bmp" in str(exc_info.value)
        finally:
            test_file.unlink()

    def test_encode_image_nonexistent_file(self) -> None:
        """Test error handling for non-existent files."""
        nonexistent_path = Path("nonexistent_image.png")

        with pytest.raises(FileNotFoundError):
            encode_image(nonexistent_path)

    @pytest.mark.parametrize("extension", SUPPORTED_IMAGE_FORMATS)
    def test_supported_image_formats(self, extension: str) -> None:
        """Test that all supported formats are accepted (without actual conversion)."""
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
            test_file = Path(f.name)
            f.write(b"fake image data")

        try:
            # Should not raise ValueError for supported formats
            result = encode_image(test_file)
            assert isinstance(result, str)
        finally:
            test_file.unlink()


class TestEncodeAudio:
    """Test suite for the encode_audio function."""

    @pytest.fixture
    def sample_mp3_path(self) -> Path:
        """Path to a sample MP3 file for testing."""
        return Path(__file__).parent.parent / "audio" / "c-IX1061gw0_1-17.mp3"

    @pytest.fixture
    def sample_m4a_path(self) -> Path:
        """Path to a sample M4A file for testing."""
        return Path(__file__).parent.parent / "audio" / "dM3lzQC_R3c.m4a"

    def test_encode_audio_supported_format(self, sample_mp3_path: Path) -> None:
        """Test encoding audio in a natively supported format (MP3)."""
        if not sample_mp3_path.exists():
            pytest.skip(f"Sample MP3 not found: {sample_mp3_path}")

        result = encode_audio(sample_mp3_path)

        # Verify it's a valid base64 string
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify we can decode it back to bytes
        decoded_data = base64.b64decode(result)
        assert len(decoded_data) > 0

        # Verify the decoded data matches the original file
        with open(sample_mp3_path, "rb") as f:
            original_data = f.read()
        assert decoded_data == original_data

    def test_encode_audio_with_string_path(self, sample_mp3_path: Path) -> None:
        """Test that string paths work as well as Path objects."""
        if not sample_mp3_path.exists():
            pytest.skip(f"Sample MP3 not found: {sample_mp3_path}")

        result = encode_audio(str(sample_mp3_path))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_audio_unsupported_format_conversion(self, sample_m4a_path: Path) -> None:
        """Test conversion of unsupported formats using ffmpeg."""
        if not sample_m4a_path.exists():
            pytest.skip(f"Sample M4A not found: {sample_m4a_path}")

        result = encode_audio(sample_m4a_path)

        # Should successfully convert and encode
        assert isinstance(result, str)
        assert len(result) > 0

        # The result should be different from the original file
        # since it was converted to MP3
        with open(sample_m4a_path, "rb") as f:
            original_data = f.read()
        original_encoded = base64.b64encode(original_data).decode("utf-8")
        assert result != original_encoded

    @patch("multimodality_app.utils.ffmpeg")
    def test_encode_audio_ffmpeg_error(self, mock_ffmpeg) -> None:
        """Test error handling when ffmpeg conversion fails."""
        # Create a fake unsupported audio file
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            test_file = Path(f.name)
            f.write(b"fake audio data")

        # Create a mock ffmpeg.Error exception
        class MockFFmpegError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.stderr = b"Mock ffmpeg error"

        # Set up the mock
        mock_ffmpeg.Error = MockFFmpegError
        mock_process = mock_ffmpeg.input.return_value.output.return_value
        mock_process.run.side_effect = MockFFmpegError("FFmpeg failed")

        try:
            with pytest.raises(RuntimeError) as exc_info:
                encode_audio(test_file)

            assert "FFmpeg conversion failed" in str(exc_info.value)
            assert "Mock ffmpeg error" in str(exc_info.value)
        finally:
            test_file.unlink()

    def test_encode_audio_nonexistent_file(self) -> None:
        """Test error handling for non-existent files."""
        nonexistent_path = Path("nonexistent_audio.mp3")

        with pytest.raises(FileNotFoundError):
            encode_audio(nonexistent_path)

    @pytest.mark.parametrize("extension", SUPPORTED_AUDIO_FORMATS)
    def test_supported_audio_formats_direct_encoding(self, extension: str) -> None:
        """Test that supported formats are encoded directly without conversion."""
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
            test_file = Path(f.name)
            f.write(b"fake audio data")

        try:
            result = encode_audio(test_file)
            assert isinstance(result, str)

            # Verify the result matches direct base64 encoding (no ffmpeg conversion)
            expected = base64.b64encode(b"fake audio data").decode("utf-8")
            assert result == expected
        finally:
            test_file.unlink()


class TestConstants:
    """Test suite for the format constants."""

    def test_supported_image_formats_not_empty(self) -> None:
        """Verify that supported image formats are defined."""
        assert len(SUPPORTED_IMAGE_FORMATS) > 0
        assert all(fmt.startswith(".") for fmt in SUPPORTED_IMAGE_FORMATS)

    def test_supported_audio_formats_not_empty(self) -> None:
        """Verify that supported audio formats are defined."""
        assert len(SUPPORTED_AUDIO_FORMATS) > 0
        assert all(fmt.startswith(".") for fmt in SUPPORTED_AUDIO_FORMATS)

    def test_expected_formats_included(self) -> None:
        """Test that expected common formats are included."""
        # Image formats
        assert ".png" in SUPPORTED_IMAGE_FORMATS
        assert ".jpg" in SUPPORTED_IMAGE_FORMATS
        assert ".jpeg" in SUPPORTED_IMAGE_FORMATS

        # Audio formats
        assert ".mp3" in SUPPORTED_AUDIO_FORMATS
        assert ".wav" in SUPPORTED_AUDIO_FORMATS
        assert ".flac" in SUPPORTED_AUDIO_FORMATS
