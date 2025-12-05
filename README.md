# QR Builder

[![CI](https://github.com/aiqso/qr-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/aiqso/qr-builder/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A production-ready Python package for generating QR codes and embedding them into images. Perfect for marketing materials, product packaging, event flyers, and website integration.

## Features

- **Generate standalone QR codes** with custom colors and sizes
- **Embed QR codes into images** with flexible positioning (center, corners)
- **Batch processing** for multiple images at once
- **REST API** via FastAPI with automatic OpenAPI documentation
- **CLI interface** for command-line usage
- **Docker support** for easy deployment
- **CORS enabled** for web integration

## Quick Start

### Installation

```bash
# From PyPI (when published)
pip install qr-builder

# From source
git clone https://github.com/aiqso/qr-builder.git
cd qr-builder
pip install -e ".[dev]"  # Include dev dependencies for testing
```

### CLI Usage

```bash
# Generate a standalone QR code
qr-builder qr "https://example.com" qr.png --size 600

# Embed QR into an image
qr-builder embed background.jpg "https://example.com" out.png \
  --scale 0.3 \
  --position bottom-right \
  --margin 30

# Batch embed into all images in a directory
qr-builder batch-embed ./images "https://example.com" ./output \
  --glob "*.jpg" \
  --position center
```

### Python Library

```python
from qr_builder import generate_qr_only, embed_qr_in_image, generate_qr

# Generate standalone QR
generate_qr_only("https://example.com", "qr.png", size=500)

# Embed QR into background image
embed_qr_in_image(
    "flyer.jpg",
    "https://example.com/product?id=123",
    "flyer_output.png",
    qr_scale=0.3,
    position="bottom-right",
    fill_color="navy",
    back_color="white",
)

# Get raw PIL Image for further processing
img = generate_qr("https://example.com", qr_size=400)
```

### REST API

Start the API server:

```bash
# Using the CLI command
qr-builder-api

# Or with uvicorn directly
uvicorn qr_builder.api:app --reload

# Visit http://127.0.0.1:8000/docs for interactive API docs
```

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/qr` | Generate standalone QR code |
| POST | `/embed` | Embed QR into uploaded image |
| POST | `/batch/embed` | Batch embed into multiple images (returns ZIP) |

**Example API call:**

```bash
# Generate QR code
curl -X POST "http://localhost:8000/qr" \
  -F "data=https://example.com" \
  -F "size=400" \
  --output qr.png

# Embed QR into image
curl -X POST "http://localhost:8000/embed" \
  -F "background=@flyer.jpg" \
  -F "data=https://example.com" \
  -F "position=bottom-right" \
  --output result.png
```

## Docker Deployment

```bash
# Build and run
docker build -t qr-builder-api .
docker run -p 8000:8000 qr-builder-api

# Or with Docker Compose
docker compose up --build
```

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `QR_BUILDER_HOST` | `0.0.0.0` | API host binding |
| `QR_BUILDER_PORT` | `8000` | API port |
| `QR_BUILDER_RELOAD` | `true` | Enable hot reload |

## Configuration Options

### QR Code Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `size` | 500 | QR code size in pixels (21-4000) |
| `fill_color` | black | Foreground color (name or hex) |
| `back_color` | white | Background color (name or hex) |

### Embedding Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `scale` | 0.3 | QR size as fraction of image width (0-1) |
| `position` | center | Placement: `center`, `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `margin` | 20 | Edge spacing in pixels |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=qr_builder

# Lint code
ruff check qr_builder/

# Type checking
mypy qr_builder/
```

## Project Structure

```
qr-builder/
├── qr_builder/
│   ├── __init__.py    # Package exports
│   ├── core.py        # Core QR generation logic
│   ├── cli.py         # Command-line interface
│   └── api.py         # FastAPI REST API
├── tests/
│   ├── test_core.py   # Core function tests
│   └── test_api.py    # API endpoint tests
├── .github/
│   └── workflows/
│       └── ci.yml     # GitHub Actions CI
├── pyproject.toml     # Package configuration
├── Dockerfile         # Docker image
├── docker-compose.yml # Docker Compose config
└── README.md
```

## Use Cases

- **Marketing flyers** - Add QR codes to promotional materials
- **Product packaging** - Link to product pages or manuals
- **Event tickets** - Embed registration/check-in links
- **Business cards** - Link to contact info or portfolios
- **Restaurant menus** - Link to online menus or ordering
- **Website widgets** - Generate QR codes dynamically via API

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
