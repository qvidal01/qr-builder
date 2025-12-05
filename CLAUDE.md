# QR Builder - Claude Code Reference

## Project Overview

QR Builder is a Python package for generating QR codes and embedding them into images. It provides a CLI, Python library, and REST API for flexible integration.

**Status:** Active Development
**Stack:** Python 3.10+, FastAPI, Pillow, qrcode
**Deploy:** Docker, Docker Compose

## Quick Commands

```bash
# Development setup
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest
pytest --cov=qr_builder

# Run API server (development)
qr-builder-api
# or: uvicorn qr_builder.api:app --reload

# Run linting
ruff check qr_builder/

# Build package
pip install build && python -m build

# Docker
docker build -t qr-builder-api .
docker compose up --build
```

## Architecture

```
qr_builder/
├── __init__.py    # Public API exports, version
├── core.py        # Core QR generation (generate_qr, embed_qr_in_image)
├── cli.py         # argparse CLI (qr, embed, batch-embed commands)
└── api.py         # FastAPI REST API with CORS
```

### Key Files

| File | Purpose |
|------|---------|
| `qr_builder/core.py` | Core business logic - QR generation, image embedding, validation |
| `qr_builder/api.py` | FastAPI app with `/qr`, `/embed`, `/batch/embed` endpoints |
| `qr_builder/cli.py` | CLI with `qr`, `embed`, `batch-embed` subcommands |
| `pyproject.toml` | Package config, dependencies, tool settings |
| `tests/test_core.py` | Unit tests for core functions |
| `tests/test_api.py` | API endpoint tests |

### Core Functions

```python
# qr_builder/core.py
generate_qr(data, qr_size=500, fill_color="black", back_color="white") -> Image
generate_qr_only(data, output_path, size=500, ...) -> Path
embed_qr_in_image(background_path, data, output_path, qr_scale=0.3, position="center", ...) -> Path
calculate_position(bg_w, bg_h, qr_size, position, margin) -> (x, y)
validate_data(data) -> None  # Raises ValueError if invalid
validate_size(size) -> None  # Raises ValueError if invalid
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/qr` | POST | Generate standalone QR (returns PNG) |
| `/embed` | POST | Embed QR into uploaded image (returns PNG) |
| `/batch/embed` | POST | Batch process multiple images (returns ZIP) |

### Constants

```python
MAX_DATA_LENGTH = 4296  # Max chars for QR
MAX_QR_SIZE = 4000      # Max pixel size
MIN_QR_SIZE = 21        # Min pixel size
VALID_POSITIONS = ("center", "top-left", "top-right", "bottom-left", "bottom-right")
```

## Dependencies

**Runtime:**
- `qrcode[pil]>=7.4.2` - QR code generation
- `Pillow>=10.0.0` - Image processing
- `fastapi>=0.115.0` - REST API framework
- `uvicorn[standard]>=0.30.0` - ASGI server

**Dev:**
- `pytest>=8.0.0` - Testing
- `pytest-cov>=4.0.0` - Coverage
- `httpx>=0.27.0` - API testing
- `ruff>=0.4.0` - Linting
- `mypy>=1.10.0` - Type checking

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QR_BUILDER_HOST` | `0.0.0.0` | API bind host |
| `QR_BUILDER_PORT` | `8000` | API port |
| `QR_BUILDER_RELOAD` | `true` | Hot reload |

## Common Tasks

### Add a new position option
1. Add to `VALID_POSITIONS` in `core.py`
2. Add calculation case in `calculate_position()`
3. Update CLI choices in `cli.py`
4. Add tests in `test_core.py`

### Add a new API endpoint
1. Add route in `api.py`
2. Use existing core functions or add new ones
3. Add tests in `test_api.py`

### Add a new CLI command
1. Add subparser in `cli.py:build_parser()`
2. Add handler in `cli.py:main()`
3. Use core functions for business logic

## Testing

```bash
# All tests
pytest

# Specific test file
pytest tests/test_core.py

# Specific test
pytest tests/test_core.py::TestGenerateQR::test_generate_qr_basic

# With coverage
pytest --cov=qr_builder --cov-report=html
```

## Deployment Notes

- Docker image exposes port 8000
- CORS enabled by default (configure `allow_origins` in production)
- Health check at `/health` for container orchestration
- Uses ERROR_CORRECT_H for maximum QR redundancy

## Git Workflow

```bash
# Feature branch
git checkout -b feature/my-feature

# Before committing
ruff check qr_builder/
pytest

# Commit
git add .
git commit -m "feat: description"
```
