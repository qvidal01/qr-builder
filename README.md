# QR Builder

[![CI](https://github.com/aiqso/qr-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/aiqso/qr-builder/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A production-ready Python package for generating QR codes with multiple artistic styles. Perfect for marketing materials, product packaging, event flyers, and website integration.

## Features

- **5 QR Code Styles:**
  - **Basic** - Simple QR codes with custom colors
  - **With Logo** - Logo/image embedded in QR center
  - **With Text** - Text/words displayed in QR center
  - **Artistic** - Image transforms INTO the QR code pattern (colorful)
  - **QArt** - Halftone/dithered artistic style

- **Multiple Interfaces:**
  - REST API via FastAPI with OpenAPI documentation
  - CLI for command-line usage
  - Web interface with visual builder
  - WordPress-embeddable widget
  - Python library for programmatic use

- **Production Ready:**
  - Docker support
  - CORS enabled for web integration
  - Batch processing for multiple images
  - Quality presets for artistic QR codes

## Quick Start

### Installation

```bash
# From source
git clone https://github.com/aiqso/qr-builder.git
cd qr-builder
pip install -e ".[dev]"  # Include dev dependencies for testing
```

### CLI Usage

```bash
# Generate a basic QR code
qr-builder qr "https://example.com" qr.png --size 600

# QR with logo in center
qr-builder logo "https://example.com" logo.png output.png --scale 0.25

# QR with text in center
qr-builder text "https://example.com" "HELLO" output.png --font-color "#e07030"

# Artistic QR (image becomes the QR pattern)
qr-builder artistic "https://example.com" image.png output.png --preset large

# QArt halftone style
qr-builder qart "https://example.com" image.png output.png --version 10

# Embed QR into background image
qr-builder embed background.jpg "https://example.com" output.png \
  --scale 0.3 --position bottom-right

# Batch embed into all images in a directory
qr-builder batch-embed ./images "https://example.com" ./output --glob "*.jpg"
```

### Python Library

```python
from qr_builder import (
    generate_qr_only,
    generate_qr_with_logo,
    generate_qr_with_text,
    generate_artistic_qr,
    generate_qart,
    generate_qr_unified,
    QRConfig,
    QRStyle,
    ARTISTIC_PRESETS,
)

# Basic QR code
generate_qr_only("https://example.com", "qr.png", size=500)

# QR with logo
generate_qr_with_logo(
    "https://example.com",
    "logo.png",
    "output.png",
    logo_scale=0.25,
)

# QR with text
generate_qr_with_text(
    "https://example.com",
    "HELLO",
    "output.png",
    font_color="#e07030",
)

# Artistic QR with preset
generate_artistic_qr(
    "https://example.com",
    "image.png",
    "output.png",
    preset="large",
    colorized=True,
)

# Unified interface with configuration
config = QRConfig(
    style=QRStyle.ARTISTIC,
    data="https://example.com",
    output_path="output.png",
    source_image="image.png",
    preset="hd",
    colorized=True,
)
generate_qr_unified(config)
```

### Web Interface

Start the visual web interface:

```bash
python server.py
# Visit http://localhost:8080
```

Features:
- Tab-based interface for all 5 QR styles
- Live preview
- Color pickers
- Preset selection for artistic QR codes
- Download generated QR codes

### REST API

Start the API server:

```bash
# Using uvicorn
uvicorn qr_builder.api:app --reload --port 8000

# Visit http://localhost:8000/docs for interactive API docs
```

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/styles` | List available styles and presets |
| POST | `/qr` | Generate basic QR code |
| POST | `/qr/text` | QR with text in center |
| POST | `/qr/logo` | QR with logo in center |
| POST | `/qr/artistic` | Artistic QR (image becomes QR) |
| POST | `/qr/qart` | Halftone/dithered QR |
| POST | `/embed` | Embed QR into background image |
| POST | `/batch/embed` | Batch embed (returns ZIP) |
| POST | `/batch/artistic` | Batch artistic QR (returns ZIP) |

See [docs/API.md](docs/API.md) for complete API documentation.

### WordPress Integration

Embed the QR Builder in any WordPress site:

1. Copy `wordpress/qr-builder-widget.html`
2. Add to WordPress via Custom HTML block
3. Update `QR_API_URL` to your server address

See [wordpress/README.md](wordpress/README.md) for detailed instructions.

## Artistic Presets

For artistic QR codes, use presets for optimal quality:

| Preset | Version | Best For |
|--------|---------|----------|
| `small` | 5 | Web thumbnails, social media |
| `medium` | 10 | General use, business cards |
| `large` | 15 | Print, marketing materials |
| `hd` | 20 | Large format, high detail |

## Docker Deployment

```bash
# Build and run
docker build -t qr-builder .
docker run -p 8080:8080 qr-builder python server.py

# Or with Docker Compose
docker compose up --build
```

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `QR_SERVER_HOST` | `0.0.0.0` | Server host binding |
| `QR_SERVER_PORT` | `8080` | Server port |

## Project Structure

```
qr-builder/
├── qr_builder/
│   ├── __init__.py      # Package exports
│   ├── core.py          # Core QR generation (5 styles)
│   ├── cli.py           # Command-line interface
│   └── api.py           # FastAPI REST API
├── server.py            # Web interface server
├── wordpress/
│   ├── qr-builder-widget.html  # WordPress embed widget
│   └── README.md               # WordPress integration guide
├── docs/
│   └── API.md           # API documentation
├── tests/
│   ├── test_core.py     # Core function tests
│   └── test_api.py      # API endpoint tests
├── .github/
│   └── workflows/
│       └── ci.yml       # GitHub Actions CI
├── pyproject.toml       # Package configuration
├── Dockerfile           # Docker image
├── docker-compose.yml   # Docker Compose config
└── README.md
```

## Use Cases

- **Marketing materials** - Branded QR codes with company images
- **Product packaging** - Artistic QR codes that match design
- **Event tickets** - Visually appealing check-in codes
- **Business cards** - QR codes with logos or text
- **Restaurant menus** - Stylish codes for online ordering
- **Social media** - Eye-catching QR codes for profiles
- **Website widgets** - Generate QR codes dynamically via API
- **WordPress sites** - Embeddable QR generator for visitors

## Requirements

- Python 3.9+
- Dependencies: qrcode, Pillow, amzqr, pyqart, segno, fastapi, uvicorn

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- **GitHub Issues:** https://github.com/Your Organization/qr-builder/issues
- **Documentation:** https://github.com/Your Organization/qr-builder
