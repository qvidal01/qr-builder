"""
qr_builder.auth
---------------

Authentication, authorization, and rate limiting for QR Builder API.

This module provides middleware and utilities for:
- API key authentication (validates tokens from your backend)
- Tier-based access control (free, pro, business)
- Rate limiting with configurable limits per tier
- Usage tracking for Odoo integration

Integration with aiqso.io:
- Your Next.js frontend sends API keys from authenticated users
- Your Odoo backend manages user tiers and tracks usage
- This module validates requests and enforces limits
"""

from __future__ import annotations

import os
import time
import hashlib
import logging
from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict

from fastapi import Request, HTTPException, Header, Depends
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration (from environment variables)
# =============================================================================

# Backend secret for webhook authentication (set this in your deployment)
BACKEND_SECRET = os.getenv("QR_BUILDER_BACKEND_SECRET", "change-me-in-production")

# Your backend URL for token validation (Odoo/Next.js backend)
BACKEND_VALIDATION_URL = os.getenv("QR_BUILDER_BACKEND_URL", "https://api.aiqso.io")

# Enable/disable authentication (disable for local development)
AUTH_ENABLED = os.getenv("QR_BUILDER_AUTH_ENABLED", "true").lower() == "true"

# Allowed origins for CORS
ALLOWED_ORIGINS = os.getenv(
    "QR_BUILDER_ALLOWED_ORIGINS",
    "https://aiqso.io,https://www.aiqso.io,https://api.aiqso.io"
).split(",")


# =============================================================================
# Tier Definitions
# =============================================================================

class UserTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ADMIN = "admin"  # Internal/backend use


@dataclass
class TierLimits:
    """Rate limits and feature access per tier."""
    requests_per_minute: int
    requests_per_day: int
    max_qr_size: int
    allowed_styles: list[str]
    batch_limit: int  # Max images in batch request
    custom_colors: bool
    priority: int  # Higher = more priority in queue


# Tier configuration - adjust these values as needed
TIER_LIMITS: dict[UserTier, TierLimits] = {
    UserTier.FREE: TierLimits(
        requests_per_minute=5,
        requests_per_day=10,
        max_qr_size=500,
        allowed_styles=["basic", "text"],  # Free: basic + text only
        batch_limit=0,  # No batch for free
        custom_colors=False,
        priority=1,
    ),
    UserTier.PRO: TierLimits(
        requests_per_minute=30,
        requests_per_day=500,
        max_qr_size=2000,
        allowed_styles=["basic", "text", "logo", "artistic", "qart", "embed"],
        batch_limit=10,
        custom_colors=True,
        priority=5,
    ),
    UserTier.BUSINESS: TierLimits(
        requests_per_minute=100,
        requests_per_day=5000,
        max_qr_size=4000,
        allowed_styles=["basic", "text", "logo", "artistic", "qart", "embed"],
        batch_limit=50,
        custom_colors=True,
        priority=10,
    ),
    UserTier.ADMIN: TierLimits(
        requests_per_minute=1000,
        requests_per_day=100000,
        max_qr_size=4000,
        allowed_styles=["basic", "text", "logo", "artistic", "qart", "embed"],
        batch_limit=100,
        custom_colors=True,
        priority=100,
    ),
}


# =============================================================================
# User Session Data
# =============================================================================

@dataclass
class UserSession:
    """Authenticated user session data."""
    user_id: str
    tier: UserTier
    api_key: str
    email: Optional[str] = None

    # Rate limiting tracking
    requests_this_minute: int = 0
    requests_today: int = 0
    minute_reset_time: float = field(default_factory=time.time)
    day_reset_time: float = field(default_factory=time.time)

    @property
    def limits(self) -> TierLimits:
        return TIER_LIMITS[self.tier]

    def check_rate_limit(self) -> tuple[bool, str]:
        """Check if user is within rate limits. Returns (allowed, reason)."""
        now = time.time()

        # Reset minute counter if minute has passed
        if now - self.minute_reset_time > 60:
            self.requests_this_minute = 0
            self.minute_reset_time = now

        # Reset daily counter if day has passed
        if now - self.day_reset_time > 86400:
            self.requests_today = 0
            self.day_reset_time = now

        # Check limits
        if self.requests_this_minute >= self.limits.requests_per_minute:
            return False, f"Rate limit exceeded: {self.limits.requests_per_minute}/minute"

        if self.requests_today >= self.limits.requests_per_day:
            return False, f"Daily limit exceeded: {self.limits.requests_per_day}/day"

        return True, "OK"

    def record_request(self) -> None:
        """Record a request for rate limiting."""
        self.requests_this_minute += 1
        self.requests_today += 1

    def can_access_style(self, style: str) -> bool:
        """Check if user's tier allows access to a style."""
        return style in self.limits.allowed_styles

    def can_use_custom_colors(self) -> bool:
        """Check if user can use custom hex colors."""
        return self.limits.custom_colors

    def get_max_batch_size(self) -> int:
        """Get maximum batch size for user's tier."""
        return self.limits.batch_limit


# =============================================================================
# In-Memory Session Store (for rate limiting)
# =============================================================================

class SessionStore:
    """
    In-memory session store for rate limiting.

    In production, consider using Redis for distributed rate limiting
    across multiple instances.
    """

    def __init__(self):
        self._sessions: dict[str, UserSession] = {}
        self._usage_log: list[dict] = []  # For Odoo sync

    def get_or_create_session(
        self,
        user_id: str,
        tier: UserTier,
        api_key: str,
        email: Optional[str] = None,
    ) -> UserSession:
        """Get existing session or create new one."""
        if api_key not in self._sessions:
            self._sessions[api_key] = UserSession(
                user_id=user_id,
                tier=tier,
                api_key=api_key,
                email=email,
            )
        else:
            # Update tier in case it changed
            self._sessions[api_key].tier = tier

        return self._sessions[api_key]

    def update_user_tier(self, api_key: str, new_tier: UserTier) -> bool:
        """Update a user's tier (called via webhook from your backend)."""
        if api_key in self._sessions:
            self._sessions[api_key].tier = new_tier
            logger.info(f"Updated tier for user to {new_tier}")
            return True
        return False

    def log_usage(
        self,
        user_id: str,
        style: str,
        success: bool,
        metadata: Optional[dict] = None,
    ) -> None:
        """Log usage for Odoo sync."""
        self._usage_log.append({
            "timestamp": time.time(),
            "user_id": user_id,
            "style": style,
            "success": success,
            "metadata": metadata or {},
        })

    def get_usage_since(self, timestamp: float) -> list[dict]:
        """Get usage logs since timestamp (for Odoo sync)."""
        return [log for log in self._usage_log if log["timestamp"] > timestamp]

    def get_user_stats(self, user_id: str) -> dict:
        """Get usage statistics for a user."""
        user_logs = [log for log in self._usage_log if log["user_id"] == user_id]
        return {
            "total_requests": len(user_logs),
            "successful": sum(1 for log in user_logs if log["success"]),
            "by_style": self._count_by_style(user_logs),
        }

    def _count_by_style(self, logs: list[dict]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for log in logs:
            counts[log["style"]] += 1
        return dict(counts)

    def clear_old_logs(self, days: int = 30) -> int:
        """Clear logs older than N days. Returns count of removed logs."""
        cutoff = time.time() - (days * 86400)
        old_count = len(self._usage_log)
        self._usage_log = [log for log in self._usage_log if log["timestamp"] > cutoff]
        return old_count - len(self._usage_log)


# Global session store
session_store = SessionStore()


# =============================================================================
# API Key Authentication
# =============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key_with_backend(api_key: str) -> Optional[dict]:
    """
    Validate API key with your backend (Odoo/Next.js).

    Your backend should return:
    {
        "valid": true,
        "user_id": "user_123",
        "tier": "pro",
        "email": "user@example.com"
    }

    Or for invalid keys:
    {
        "valid": false,
        "error": "Invalid or expired API key"
    }
    """
    # For development/testing without backend
    if not AUTH_ENABLED:
        return {
            "valid": True,
            "user_id": "dev_user",
            "tier": "business",
            "email": "dev@aiqso.io",
        }

    # Check for internal/admin keys (for your backend services)
    if api_key.startswith("qrb_admin_"):
        expected_hash = hashlib.sha256(
            f"{BACKEND_SECRET}:{api_key}".encode()
        ).hexdigest()[:16]
        if api_key.endswith(expected_hash):
            return {
                "valid": True,
                "user_id": "admin",
                "tier": "admin",
                "email": "admin@aiqso.io",
            }

    # Validate with your backend
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_VALIDATION_URL}/api/qr-builder/validate-key",
                json={"api_key": api_key},
                headers={"Authorization": f"Bearer {BACKEND_SECRET}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Backend validation failed: {e}")

    return None


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
) -> UserSession:
    """
    Dependency to get current authenticated user.

    Usage in endpoints:
        @app.post("/qr/logo")
        async def create_logo_qr(user: UserSession = Depends(get_current_user)):
            if not user.can_access_style("logo"):
                raise HTTPException(403, "Upgrade to Pro for logo QR codes")
    """
    # Allow unauthenticated access for free tier (with limits)
    if not api_key:
        if not AUTH_ENABLED:
            # Dev mode - return business tier
            return session_store.get_or_create_session(
                user_id="anonymous",
                tier=UserTier.BUSINESS,
                api_key="dev_anonymous",
            )

        # Production - anonymous users get free tier
        client_ip = request.client.host if request.client else "unknown"
        anonymous_key = f"anon_{hashlib.md5(client_ip.encode()).hexdigest()[:8]}"
        return session_store.get_or_create_session(
            user_id=f"anonymous_{client_ip}",
            tier=UserTier.FREE,
            api_key=anonymous_key,
        )

    # Validate API key with backend
    validation = await validate_api_key_with_backend(api_key)

    if not validation or not validation.get("valid"):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Get your key at https://aiqso.io/portal",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Get or create session
    tier = UserTier(validation.get("tier", "free"))
    return session_store.get_or_create_session(
        user_id=validation["user_id"],
        tier=tier,
        api_key=api_key,
        email=validation.get("email"),
    )


async def require_auth(
    user: UserSession = Depends(get_current_user),
) -> UserSession:
    """Dependency that requires authentication (no anonymous access)."""
    if user.user_id.startswith("anonymous"):
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Sign up at https://aiqso.io/portal",
        )
    return user


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

async def check_rate_limit(user: UserSession = Depends(get_current_user)) -> UserSession:
    """
    Dependency to check rate limits.

    Usage:
        @app.post("/qr")
        async def create_qr(user: UserSession = Depends(check_rate_limit)):
            ...
    """
    allowed, reason = user.check_rate_limit()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {reason}. Upgrade at https://aiqso.io/portal",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(user.limits.requests_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )

    user.record_request()
    return user


# =============================================================================
# Style Access Control
# =============================================================================

def require_style(style: str) -> Callable:
    """
    Dependency factory to check style access.

    Usage:
        @app.post("/qr/logo")
        async def create_logo_qr(
            user: UserSession = Depends(require_style("logo"))
        ):
            ...
    """
    async def check_style_access(
        user: UserSession = Depends(check_rate_limit),
    ) -> UserSession:
        if not user.can_access_style(style):
            raise HTTPException(
                status_code=403,
                detail=f"'{style}' style requires Pro or Business tier. "
                       f"Upgrade at https://aiqso.io/portal",
                headers={"X-Required-Tier": "pro"},
            )
        return user

    return check_style_access


def require_custom_colors() -> Callable:
    """Dependency to check if custom colors are allowed."""
    async def check_custom_colors(
        user: UserSession = Depends(check_rate_limit),
        fill_color: str = "",
        back_color: str = "",
    ) -> UserSession:
        # Check if using hex colors
        is_custom = (
            fill_color.startswith("#") or
            back_color.startswith("#")
        )
        if is_custom and not user.can_use_custom_colors():
            raise HTTPException(
                status_code=403,
                detail="Custom hex colors require Pro or Business tier. "
                       "Upgrade at https://aiqso.io/portal",
            )
        return user

    return check_custom_colors


# =============================================================================
# Webhook Authentication (for your backend)
# =============================================================================

async def verify_backend_webhook(
    x_webhook_secret: str = Header(..., alias="X-Webhook-Secret"),
) -> bool:
    """
    Verify webhook requests from your backend.

    Your backend should include the secret in the X-Webhook-Secret header.
    """
    if x_webhook_secret != BACKEND_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook secret",
        )
    return True


# =============================================================================
# Helper Functions
# =============================================================================

def get_tier_info(tier: UserTier) -> dict:
    """Get tier information for display."""
    limits = TIER_LIMITS[tier]
    return {
        "tier": tier.value,
        "limits": {
            "requests_per_minute": limits.requests_per_minute,
            "requests_per_day": limits.requests_per_day,
            "max_qr_size": limits.max_qr_size,
            "batch_limit": limits.batch_limit,
        },
        "features": {
            "allowed_styles": limits.allowed_styles,
            "custom_colors": limits.custom_colors,
        },
    }


def get_all_tiers_info() -> list[dict]:
    """Get information about all tiers for pricing page."""
    return [
        {
            "tier": tier.value,
            "limits": {
                "requests_per_minute": limits.requests_per_minute,
                "requests_per_day": limits.requests_per_day,
                "max_qr_size": limits.max_qr_size,
                "batch_limit": limits.batch_limit,
            },
            "features": {
                "allowed_styles": limits.allowed_styles,
                "custom_colors": limits.custom_colors,
            },
        }
        for tier, limits in TIER_LIMITS.items()
        if tier != UserTier.ADMIN  # Don't expose admin tier
    ]
