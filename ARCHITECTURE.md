# QR Builder Architecture

This document describes the architecture and design decisions of the QR Builder project.

## Overview

QR Builder is a Python package for generating QR codes with various artistic styles. It provides three interfaces:

1. **Python Library** - For programmatic use in Python applications
2. **CLI** - Command-line interface for scripts and automation
3. **REST API** - HTTP API for web integrations

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                    │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│   CLI Client    │  Python Import  │   HTTP Client   │  WordPress Widget     │
│   (qr-builder)  │  (library)      │   (cURL, etc)   │  (JS Frontend)        │
└────────┬────────┴────────┬────────┴────────┬────────┴───────────┬───────────┘
         │                 │                 │                     │
         ▼                 ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Interface Layer                                    │
├─────────────────┬─────────────────┬─────────────────────────────────────────┤
│    cli.py       │    core.py      │              api.py                     │
│  (CLI Parser)   │  (Direct Use)   │          (FastAPI Routes)               │
└────────┬────────┴────────┬────────┴────────┬────────────────────────────────┘
         │                 │                 │
         └────────────────┬┴─────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Core Layer                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                           core.py                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ generate_qr │  │generate_qr_ │  │generate_qr_ │  │generate_    │        │
│  │             │  │ with_logo   │  │ with_text   │  │ artistic_qr │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │generate_qart│  │embed_qr_in_ │  │ validate_*  │                         │
│  │             │  │   image     │  │  functions  │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         External Libraries                                   │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│   qrcode    │   Pillow    │   amzqr     │   pyqart    │   segno             │
│  (QR Gen)   │ (Image Ops) │ (Artistic)  │ (Halftone)  │ (Advanced QR)       │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────────┘
```

## Module Structure

```
qr_builder/
├── __init__.py      # Package exports and version
├── config.py        # Centralized configuration management
├── core.py          # Core QR generation functions
├── cli.py           # Command-line interface
├── api.py           # FastAPI REST API
├── auth.py          # Authentication and rate limiting
└── utils.py         # Utility functions (file validation, etc.)
```

### Module Responsibilities

#### `config.py`
- Centralized configuration loading from environment variables
- Configuration validation
- Type-safe configuration objects
- Singleton pattern for global config access

#### `core.py`
- All QR code generation logic
- Image manipulation functions
- Input validation functions
- Style-specific generators (basic, logo, text, artistic, qart, embed)

#### `cli.py`
- argparse-based CLI
- Subcommands for each QR style
- Batch processing support
- Logging configuration

#### `api.py`
- FastAPI application
- REST endpoints for all styles
- File upload handling
- OpenAPI documentation
- CORS configuration

#### `auth.py`
- API key authentication
- Tier-based access control (free, pro, business)
- Rate limiting per tier
- Session management
- Backend webhook integration

#### `utils.py`
- File upload validation
- MIME type detection
- Temporary file management
- Context managers for resource cleanup

## QR Code Styles

The system supports five distinct QR code styles:

| Style | Description | Required Input | Tier |
|-------|-------------|----------------|------|
| **Basic** | Simple QR with custom colors | Data only | Free |
| **Text** | Text/words in QR center | Data + text | Free |
| **Logo** | Logo embedded in center | Data + logo image | Pro |
| **Artistic** | Image blended into QR pattern | Data + image | Pro |
| **QArt** | Halftone/dithered style | Data + image | Pro |
| **Embed** | QR placed on background | Data + background | Pro |

## Authentication Flow

```
┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐
│  Client   │──────│  API      │──────│  Auth     │──────│  Backend  │
│           │      │  Gateway  │      │  Module   │      │  (your-org)  │
└───────────┘      └───────────┘      └───────────┘      └───────────┘
      │                  │                  │                  │
      │  Request + Key   │                  │                  │
      │─────────────────>│                  │                  │
      │                  │  Validate Key    │                  │
      │                  │─────────────────>│                  │
      │                  │                  │  POST /validate  │
      │                  │                  │─────────────────>│
      │                  │                  │                  │
      │                  │                  │  User + Tier     │
      │                  │                  │<─────────────────│
      │                  │  Session + Tier  │                  │
      │                  │<─────────────────│                  │
      │                  │                  │                  │
      │                  │  Check Rate Limit│                  │
      │                  │─────────────────>│                  │
      │                  │                  │                  │
      │                  │  Check Style     │                  │
      │                  │  Access          │                  │
      │                  │─────────────────>│                  │
      │                  │                  │                  │
      │    Response      │                  │                  │
      │<─────────────────│                  │                  │
```

## Rate Limiting

Rate limits are enforced per tier:

| Tier | Requests/Minute | Requests/Day | Max Size | Batch Limit |
|------|-----------------|--------------|----------|-------------|
| Free | 5 | 10 | 500px | 0 |
| Pro | 30 | 500 | 2000px | 10 |
| Business | 100 | 5000 | 4000px | 50 |
| Admin | 1000 | 100000 | 4000px | 100 |

## Data Flow

### QR Generation Flow

```
User Input
    │
    ▼
┌─────────────────┐
│ Input Validation│ ◄── validate_data(), validate_size()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ QR Code Creation│ ◄── qrcode library
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Style Processing│ ◄── Style-specific logic (logo, artistic, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Image Output    │ ◄── Pillow save to PNG
└────────┬────────┘
         │
         ▼
PNG Binary / File
```

### API Request Flow

```
HTTP Request
    │
    ▼
┌─────────────────┐
│ CORS Middleware │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Authentication  │ ◄── get_current_user()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Rate Limiting   │ ◄── check_rate_limit()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Style Access    │ ◄── require_style()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ File Validation │ ◄── validate_upload_file()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Core Generation │ ◄── generate_* functions
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Usage Logging   │ ◄── session_store.log_usage()
└────────┬────────┘
         │
         ▼
HTTP Response (PNG)
```

## Configuration

Configuration is managed through environment variables with a centralized `config.py` module:

```python
from qr_builder.config import get_config

config = get_config()
print(config.server.port)           # 8000
print(config.security.auth_enabled) # True/False
print(config.qr.max_qr_size)        # 4000
```

See `.env.example` for all available configuration options.

## External Dependencies

### Runtime Dependencies
- **qrcode** - Base QR code generation
- **Pillow** - Image processing
- **FastAPI** - REST API framework
- **uvicorn** - ASGI server
- **httpx** - HTTP client for backend validation
- **amzqr** - Artistic QR generation
- **pyqart** - Halftone/dithered QR generation
- **segno** - Advanced QR features

### Development Dependencies
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting
- **ruff** - Linting
- **mypy** - Type checking

## Security Considerations

1. **Input Validation** - All user inputs are validated before processing
2. **File Uploads** - MIME type detection, size limits, and content validation
3. **Subprocess Security** - External commands use validated parameters with timeouts
4. **Authentication** - API key validation with backend integration
5. **Rate Limiting** - Per-tier limits to prevent abuse
6. **CORS** - Configurable origins for production
7. **Secrets** - Constant-time comparison for webhook secrets
8. **Non-root Container** - Docker runs as non-root user

## Deployment Architecture

### Docker Deployment

```
┌─────────────────────────────────────────────────────┐
│                    Docker Host                       │
│  ┌───────────────────────────────────────────────┐  │
│  │          QR Builder Container                  │  │
│  │  ┌──────────────────────────────────────────┐ │  │
│  │  │              Python 3.11                  │ │  │
│  │  │  ┌────────────────────────────────────┐  │ │  │
│  │  │  │       FastAPI Application          │  │ │  │
│  │  │  │                                    │  │ │  │
│  │  │  │  - Uvicorn ASGI Server             │  │ │  │
│  │  │  │  - QR Builder Core                 │  │ │  │
│  │  │  │  - Auth Module                     │  │ │  │
│  │  │  └────────────────────────────────────┘  │ │  │
│  │  └──────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────┘  │
│                        │                             │
│                        ▼                             │
│                   Port 8000                          │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
              External Load Balancer / Reverse Proxy
```

### Production Considerations

1. **Scaling** - Horizontal scaling via container orchestration
2. **Load Balancing** - Use nginx or cloud load balancer
3. **TLS** - Terminate SSL at reverse proxy
4. **Monitoring** - Health check endpoint at `/health`
5. **Logging** - Structured logging with configurable levels
6. **Memory** - Recommended 512MB per container
7. **Storage** - Stateless design; temp files cleaned up automatically

## Future Considerations

1. **Redis Integration** - For distributed rate limiting and caching
2. **Async Workers** - Celery for long-running batch operations
3. **CDN** - Cache generated QR codes at edge
4. **Metrics** - Prometheus integration for monitoring
5. **Webhooks** - Async notifications for batch completion
