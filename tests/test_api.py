"""Tests for qr_builder.api module."""

import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io

from qr_builder.api import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestQREndpoint:
    """Tests for the /qr endpoint."""

    def test_create_qr_basic(self, client):
        response = client.post("/qr", data={"data": "https://example.com"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Verify it's a valid PNG image
        img = Image.open(io.BytesIO(response.content))
        assert img.format == "PNG"
        assert img.size == (500, 500)  # Default size

    def test_create_qr_custom_size(self, client):
        response = client.post("/qr", data={"data": "test", "size": 300})
        assert response.status_code == 200

        img = Image.open(io.BytesIO(response.content))
        assert img.size == (300, 300)

    def test_create_qr_custom_colors(self, client):
        response = client.post(
            "/qr",
            data={
                "data": "test",
                "fill_color": "blue",
                "back_color": "yellow",
            },
        )
        assert response.status_code == 200

    def test_create_qr_empty_data(self, client):
        response = client.post("/qr", data={"data": ""})
        assert response.status_code == 400


class TestEmbedEndpoint:
    """Tests for the /embed endpoint."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample image in memory."""
        img = Image.new("RGB", (800, 600), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    def test_embed_qr_basic(self, client, sample_image):
        response = client.post(
            "/embed",
            data={"data": "https://example.com"},
            files={"background": ("test.png", sample_image, "image/png")},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        img = Image.open(io.BytesIO(response.content))
        assert img.size == (800, 600)

    def test_embed_qr_invalid_scale(self, client, sample_image):
        response = client.post(
            "/embed",
            data={"data": "test", "scale": 1.5},
            files={"background": ("test.png", sample_image, "image/png")},
        )
        assert response.status_code == 400


class TestBatchEmbedEndpoint:
    """Tests for the /batch/embed endpoint."""

    @pytest.fixture
    def sample_images(self):
        """Create multiple sample images."""
        images = []
        for i in range(3):
            img = Image.new("RGB", (400 + i * 100, 300 + i * 50), color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            images.append((f"image_{i}.png", buf, "image/png"))
        return images

    def test_batch_embed_returns_zip(self, client, sample_images):
        response = client.post(
            "/batch/embed",
            data={"data": "https://example.com"},
            files=[("backgrounds", img) for img in sample_images],
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
