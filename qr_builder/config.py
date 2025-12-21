"""
qr_builder.config
-----------------

Centralized configuration management for QR Builder.

All configuration is loaded from environment variables with sensible defaults
for development. In production, these should be set via environment variables
or a .env file.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _parse_bool(value: str) -> bool:
    """Parse boolean from environment variable string."""
    return value.lower() in ("true", "1", "yes", "on")


def _parse_list(value: str) -> list[str]:
    """Parse comma-separated list from environment variable."""
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "info"


@dataclass(frozen=True)
class SecurityConfig:
    """Security-related configuration."""
    auth_enabled: bool = True
    backend_secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    backend_url: str = "https://your-backend.example.com"
    allowed_origins: list[str] = field(default_factory=list)

    # File upload limits
    max_upload_size_mb: int = 10
    allowed_image_types: tuple = ("image/png", "image/jpeg", "image/gif", "image/webp")

    def __post_init__(self):
        # Warn about insecure defaults in production
        if self.auth_enabled and self.backend_secret == "change-me-in-production":
            logger.warning(
                "SECURITY WARNING: Using default backend secret. "
                "Set QR_BUILDER_BACKEND_SECRET environment variable in production."
            )


@dataclass(frozen=True)
class QRConfig:
    """QR code generation limits and defaults."""
    max_data_length: int = 4296
    max_qr_size: int = 4000
    min_qr_size: int = 21
    default_size: int = 500
    max_batch_size: int = 100


@dataclass
class AppConfig:
    """Main application configuration."""
    server: ServerConfig
    security: SecurityConfig
    qr: QRConfig

    # Environment
    environment: str = "development"
    debug: bool = False

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration from environment variables."""
        environment = os.getenv("QR_BUILDER_ENV", "development")
        is_production = environment == "production"

        # Server config
        server = ServerConfig(
            host=os.getenv("QR_BUILDER_HOST", "0.0.0.0"),
            port=int(os.getenv("QR_BUILDER_PORT", "8000")),
            reload=_parse_bool(os.getenv("QR_BUILDER_RELOAD", "false" if is_production else "true")),
            workers=int(os.getenv("QR_BUILDER_WORKERS", "4" if is_production else "1")),
            log_level=os.getenv("QR_BUILDER_LOG_LEVEL", "info"),
        )

        # Security config
        backend_secret = os.getenv("QR_BUILDER_BACKEND_SECRET", "")
        if not backend_secret:
            if is_production:
                raise ValueError(
                    "QR_BUILDER_BACKEND_SECRET must be set in production environment"
                )
            backend_secret = "dev-secret-not-for-production"

        allowed_origins_default = (
            "https://your-domain.example.com,https://www.aiqso.io,https://your-backend.example.com"
            if is_production
            else "*"
        )

        security = SecurityConfig(
            auth_enabled=_parse_bool(os.getenv("QR_BUILDER_AUTH_ENABLED", "true" if is_production else "false")),
            backend_secret=backend_secret,
            backend_url=os.getenv("QR_BUILDER_BACKEND_URL", "https://your-backend.example.com"),
            allowed_origins=_parse_list(os.getenv("QR_BUILDER_ALLOWED_ORIGINS", allowed_origins_default)),
            max_upload_size_mb=int(os.getenv("QR_BUILDER_MAX_UPLOAD_MB", "10")),
        )

        # QR config
        qr = QRConfig(
            max_data_length=int(os.getenv("QR_BUILDER_MAX_DATA_LENGTH", "4296")),
            max_qr_size=int(os.getenv("QR_BUILDER_MAX_QR_SIZE", "4000")),
            min_qr_size=int(os.getenv("QR_BUILDER_MIN_QR_SIZE", "21")),
            default_size=int(os.getenv("QR_BUILDER_DEFAULT_SIZE", "500")),
            max_batch_size=int(os.getenv("QR_BUILDER_MAX_BATCH_SIZE", "100")),
        )

        return cls(
            server=server,
            security=security,
            qr=qr,
            environment=environment,
            debug=_parse_bool(os.getenv("QR_BUILDER_DEBUG", "false")),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if self.server.port < 1 or self.server.port > 65535:
            issues.append(f"Invalid port: {self.server.port}")

        if self.qr.min_qr_size >= self.qr.max_qr_size:
            issues.append("min_qr_size must be less than max_qr_size")

        if self.qr.max_batch_size < 1:
            issues.append("max_batch_size must be at least 1")

        if self.security.max_upload_size_mb < 1:
            issues.append("max_upload_size_mb must be at least 1")

        if self.environment == "production":
            if "*" in self.security.allowed_origins:
                issues.append("Wildcard CORS origins not allowed in production")
            if self.security.backend_secret == "dev-secret-not-for-production":
                issues.append("Backend secret not set for production")

        return issues


# Global configuration instance (lazy loaded)
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the application configuration (lazy loaded singleton)."""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
        issues = _config.validate()
        if issues:
            for issue in issues:
                logger.error(f"Configuration error: {issue}")
            if _config.environment == "production":
                raise ValueError(f"Configuration validation failed: {issues}")
    return _config


def reset_config() -> None:
    """Reset configuration (useful for testing)."""
    global _config
    _config = None
