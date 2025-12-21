# QR Builder Installation Guide

This guide covers various methods to install and run QR Builder.

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
  - [From Source (Development)](#from-source-development)
  - [Using pip](#using-pip)
  - [Using Docker](#using-docker)
  - [Using Docker Compose](#using-docker-compose)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Requirements

### System Requirements
- Python 3.10 or higher
- pip (Python package manager)
- 512MB RAM minimum (1GB recommended)
- 500MB disk space

### Optional Requirements
- Docker and Docker Compose (for containerized deployment)
- Git (for source installation)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Your Organization/qr-builder.git
cd qr-builder

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Run the API server
uvicorn qr_builder.api:app --reload --port 8000

# Visit http://localhost:8000/docs for API documentation
```

## Installation Methods

### From Source (Development)

This is the recommended method for development and testing.

```bash
# 1. Clone the repository
git clone https://github.com/Your Organization/qr-builder.git
cd qr-builder

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 4. Install in development mode with dev dependencies
pip install -e ".[dev]"

# 5. Verify installation
qr-builder --help
python -c "from qr_builder import __version__; print(f'QR Builder v{__version__}')"
```

### Using pip

For production use without modifying the source:

```bash
# Install from source directory
pip install /path/to/qr-builder

# Or if published to PyPI (future):
# pip install qr-builder
```

### Using Docker

Build and run using Docker:

```bash
# Build the Docker image
docker build -t qr-builder .

# Run the container
docker run -p 8000:8000 qr-builder

# Run with environment variables
docker run -p 8000:8000 \
  -e QR_BUILDER_AUTH_ENABLED=false \
  -e QR_BUILDER_MAX_UPLOAD_MB=20 \
  qr-builder

# Run with web interface instead of API
docker run -p 8080:8080 \
  -e QR_SERVER_PORT=8080 \
  qr-builder python server.py
```

### Using Docker Compose

For easy deployment with configuration:

```bash
# 1. Copy the example environment file
cp .env.example .env

# 2. Edit .env with your settings
nano .env

# 3. Start the services
docker compose up -d

# 4. View logs
docker compose logs -f

# 5. Stop the services
docker compose down
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Copy example configuration
cp .env.example .env
```

Key configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
| `QR_BUILDER_ENV` | `development` | Environment (development/production) |
| `QR_BUILDER_HOST` | `0.0.0.0` | Server bind host |
| `QR_BUILDER_PORT` | `8000` | Server port |
| `QR_BUILDER_AUTH_ENABLED` | `false` (dev) | Enable API key authentication |
| `QR_BUILDER_BACKEND_SECRET` | - | Secret for webhook auth (required in production) |
| `QR_BUILDER_ALLOWED_ORIGINS` | `*` | CORS allowed origins |
| `QR_BUILDER_MAX_UPLOAD_MB` | `10` | Maximum upload file size |

See `.env.example` for all available options.

### Production Configuration

For production deployments:

```bash
# Required settings
export QR_BUILDER_ENV=production
export QR_BUILDER_AUTH_ENABLED=true
export QR_BUILDER_BACKEND_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export QR_BUILDER_ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

## Running the Application

### REST API Server

```bash
# Development (with hot reload)
uvicorn qr_builder.api:app --reload --port 8000

# Production
uvicorn qr_builder.api:app --host 0.0.0.0 --port 8000 --workers 4

# Using the CLI entry point
qr-builder-api
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Web Interface

```bash
# Start the web interface server
python server.py

# Or with custom port
QR_SERVER_PORT=8080 python server.py
```

Visit `http://localhost:8080` for the web interface.

### CLI Usage

```bash
# Generate a basic QR code
qr-builder qr "https://example.com" output.png

# Generate QR with logo
qr-builder logo logo.png "https://example.com" output.png

# See all commands
qr-builder --help
```

## Verification

### Test the Installation

```bash
# Run the test suite
pytest

# Run with coverage
pytest --cov=qr_builder --cov-report=html

# Run linting
ruff check qr_builder/
```

### Verify API

```bash
# Check health endpoint
curl http://localhost:8000/health

# Generate a QR code
curl -X POST "http://localhost:8000/qr" \
  -F "data=https://example.com" \
  --output test_qr.png

# Check the generated file
file test_qr.png  # Should show: PNG image data, 500 x 500
```

### Verify CLI

```bash
# Generate a QR code
qr-builder qr "Hello World" hello.png

# Check the output
ls -la hello.png
```

## Troubleshooting

### Common Issues

#### Import Errors

```
ModuleNotFoundError: No module named 'qr_builder'
```

**Solution:** Ensure you've activated your virtual environment and installed the package:
```bash
source .venv/bin/activate
pip install -e .
```

#### Permission Denied (Docker)

```
PermissionError: [Errno 13] Permission denied
```

**Solution:** The Docker container runs as non-root user. Ensure mounted volumes have correct permissions:
```bash
chmod -R 755 /path/to/mounted/volume
```

#### pyqart Not Found

```
RuntimeError: pyqart command not found
```

**Solution:** Install the pyqart package:
```bash
pip install pyqart
```

#### amzqr Import Error

```
ModuleNotFoundError: No module named 'amzqr'
```

**Solution:** Install the amzqr package:
```bash
pip install amzqr
```

#### Port Already in Use

```
OSError: [Errno 98] Address already in use
```

**Solution:** Either stop the existing process or use a different port:
```bash
# Find the process
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use a different port
uvicorn qr_builder.api:app --port 8001
```

### Getting Help

- **GitHub Issues:** https://github.com/Your Organization/qr-builder/issues
- **Documentation:** See `README.md` and `docs/API.md`
- **Architecture:** See `ARCHITECTURE.md`

### Logs

Enable debug logging for troubleshooting:

```bash
export QR_BUILDER_LOG_LEVEL=debug
export QR_BUILDER_DEBUG=true
uvicorn qr_builder.api:app --log-level debug
```

## Next Steps

After installation:

1. Read the [README.md](README.md) for usage examples
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Check [docs/API.md](docs/API.md) for API reference
4. Set up authentication for production use
