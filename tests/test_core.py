"""Tests for qr_builder.core module."""

import pytest
from PIL import Image
from pathlib import Path
import tempfile

from qr_builder.core import (
    generate_qr,
    generate_qr_only,
    embed_qr_in_image,
    calculate_position,
    validate_data,
    validate_size,
    MAX_DATA_LENGTH,
    MAX_QR_SIZE,
    MIN_QR_SIZE,
)


class TestValidation:
    """Tests for input validation functions."""

    def test_validate_data_empty(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_data("")

    def test_validate_data_whitespace(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_data("   ")

    def test_validate_data_too_long(self):
        data = "a" * (MAX_DATA_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_data(data)

    def test_validate_data_valid(self):
        validate_data("https://example.com")  # Should not raise

    def test_validate_size_too_small(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_size(MIN_QR_SIZE - 1)

    def test_validate_size_too_large(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_size(MAX_QR_SIZE + 1)

    def test_validate_size_valid(self):
        validate_size(500)  # Should not raise


class TestGenerateQR:
    """Tests for QR code generation."""

    def test_generate_qr_basic(self):
        img = generate_qr("https://example.com")
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"
        assert img.size == (500, 500)  # Default size

    def test_generate_qr_custom_size(self):
        img = generate_qr("test data", qr_size=300)
        assert img.size == (300, 300)

    def test_generate_qr_empty_data(self):
        with pytest.raises(ValueError):
            generate_qr("")


class TestGenerateQROnly:
    """Tests for standalone QR generation."""

    def test_generate_qr_only_creates_file(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = generate_qr_only("https://example.com", output_path)
            assert result.exists()
            assert result.suffix == ".png"

            # Verify it's a valid image
            img = Image.open(result)
            assert img.size == (500, 500)
        finally:
            output_path.unlink(missing_ok=True)


class TestCalculatePosition:
    """Tests for position calculation."""

    def test_center_position(self):
        x, y = calculate_position(1000, 800, 200, "center", 20)
        assert x == 400  # (1000 - 200) // 2
        assert y == 300  # (800 - 200) // 2

    def test_top_left_position(self):
        x, y = calculate_position(1000, 800, 200, "top-left", 20)
        assert x == 20  # margin
        assert y == 20  # margin

    def test_top_right_position(self):
        x, y = calculate_position(1000, 800, 200, "top-right", 20)
        assert x == 780  # 1000 - 200 - 20
        assert y == 20

    def test_bottom_left_position(self):
        x, y = calculate_position(1000, 800, 200, "bottom-left", 20)
        assert x == 20
        assert y == 580  # 800 - 200 - 20

    def test_bottom_right_position(self):
        x, y = calculate_position(1000, 800, 200, "bottom-right", 20)
        assert x == 780
        assert y == 580

    def test_invalid_position(self):
        with pytest.raises(ValueError, match="Unsupported position"):
            calculate_position(1000, 800, 200, "invalid", 20)

    def test_case_insensitive(self):
        x1, y1 = calculate_position(1000, 800, 200, "CENTER", 20)
        x2, y2 = calculate_position(1000, 800, 200, "center", 20)
        assert x1 == x2
        assert y1 == y2


class TestEmbedQR:
    """Tests for embedding QR into images."""

    @pytest.fixture
    def background_image(self):
        """Create a temporary background image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (800, 600), color="white")
            img.save(f.name)
            yield Path(f.name)
        Path(f.name).unlink(missing_ok=True)

    def test_embed_qr_basic(self, background_image):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = embed_qr_in_image(
                background_image,
                "https://example.com",
                output_path,
            )
            assert result.exists()

            img = Image.open(result)
            assert img.size == (800, 600)  # Same as background
        finally:
            output_path.unlink(missing_ok=True)

    def test_embed_qr_invalid_scale(self, background_image):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="qr_scale must be between"):
                embed_qr_in_image(
                    background_image,
                    "test",
                    output_path,
                    qr_scale=1.5,
                )
        finally:
            output_path.unlink(missing_ok=True)

    def test_embed_qr_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            embed_qr_in_image(
                "/nonexistent/path.png",
                "test",
                "/tmp/out.png",
            )
